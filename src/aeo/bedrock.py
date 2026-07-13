"""Claude-on-Bedrock client used by all experiments.

Uses the Converse API so tool use works uniformly across Claude versions.
Newer Anthropic models on Bedrock are invoked through cross-region inference
profiles (the ``us.`` prefix); if a bare foundation-model id is rejected, the
client retries once with the prefix and caches the working id.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Any, Callable

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

DEFAULT_REGION = "us-east-1"

# Short aliases so experiment configs stay readable.
MODELS = {
    "haiku-4.5": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "sonnet-4.5": "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
    "sonnet-4": "us.anthropic.claude-sonnet-4-20250514-v1:0",
    "opus-4.5": "us.anthropic.claude-opus-4-5-20251101-v1:0",
    "opus-4.1": "us.anthropic.claude-opus-4-1-20250805-v1:0",
}

_RETRYABLE = ("ThrottlingException", "ServiceUnavailableException", "ModelNotReadyException")


def _is_retryable(exc: BaseException) -> bool:
    return (
        isinstance(exc, ClientError)
        and exc.response.get("Error", {}).get("Code") in _RETRYABLE
    )


@dataclass
class ToolCall:
    tool_use_id: str
    name: str
    input: dict


@dataclass
class Turn:
    """One assistant message: its text, any tool calls, and raw content blocks."""

    text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    content: list[dict]
    usage: dict


@dataclass
class Conversation:
    """Full multi-round exchange, including tool results the model saw."""

    final_text: str
    turns: list[Turn]
    messages: list[dict]
    total_usage: dict = field(default_factory=dict)
    # True if the model was still requesting tools when the round budget ran
    # out and we forced a no-tool final answer. Aggressive searching is itself
    # a signal, so this is surfaced rather than hidden.
    forced_answer: bool = False

    @property
    def tool_calls(self) -> list[ToolCall]:
        return [c for t in self.turns for c in t.tool_calls]


class ClaudeClient:
    def __init__(
        self,
        model: str = "sonnet-4.5",
        region: str = DEFAULT_REGION,
        temperature: float = 0.0,
        max_tokens: int = 2048,
    ):
        self.model_id = MODELS.get(model, model)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._rt = boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(retries={"max_attempts": 0}, read_timeout=300),
        )

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=2, min=2, max=60),
        stop=stop_after_attempt(8),
        reraise=True,
    )
    def _converse_raw(self, **kwargs) -> dict:
        try:
            return self._rt.converse(**kwargs)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            # Bare foundation-model ids often require the inference-profile prefix.
            if code == "ValidationException" and not kwargs["modelId"].startswith("us."):
                kwargs["modelId"] = "us." + kwargs["modelId"]
                self.model_id = kwargs["modelId"]
                return self._rt.converse(**kwargs)
            raise

    def converse(
        self,
        messages: list[dict],
        system: str | None = None,
        tools: list[dict] | None = None,
        temperature: float | None = None,
    ) -> Turn:
        kwargs: dict[str, Any] = {
            "modelId": self.model_id,
            "messages": messages,
            "inferenceConfig": {
                "temperature": self.temperature if temperature is None else temperature,
                "maxTokens": self.max_tokens,
            },
        }
        if system:
            kwargs["system"] = [{"text": system}]
        if tools:
            kwargs["toolConfig"] = {"tools": tools}

        resp = self._converse_raw(**kwargs)
        content = resp["output"]["message"]["content"]
        text = "".join(b["text"] for b in content if "text" in b)
        calls = [
            ToolCall(b["toolUse"]["toolUseId"], b["toolUse"]["name"], b["toolUse"]["input"])
            for b in content
            if "toolUse" in b
        ]
        return Turn(
            text=text,
            tool_calls=calls,
            stop_reason=resp["stopReason"],
            content=content,
            usage=resp.get("usage", {}),
        )

    def run(
        self,
        prompt: str,
        system: str | None = None,
        tools: list[dict] | None = None,
        tool_executor: Callable[[str, dict], str] | None = None,
        temperature: float | None = None,
        max_rounds: int = 10,
    ) -> Conversation:
        """Run a prompt to completion, executing tool calls via ``tool_executor``.

        If the model is still requesting tools after ``max_rounds`` (it can search
        very aggressively when retrieved evidence conflicts with a strong prior),
        we make one final call with tools withheld so it must answer from what it
        has gathered — mirroring how production answer engines cap tool use. The
        returned Conversation flags this via ``forced_answer``.
        """
        messages: list[dict] = [{"role": "user", "content": [{"text": prompt}]}]
        turns: list[Turn] = []
        usage: dict[str, int] = {}
        gathered: list[str] = []  # tool-result texts, for the forced fallback
        forced = False

        def accrue(turn: Turn) -> None:
            turns.append(turn)
            for k, v in turn.usage.items():
                if isinstance(v, int):
                    usage[k] = usage.get(k, 0) + v
            messages.append({"role": "assistant", "content": copy.deepcopy(turn.content)})

        pending_tools = False
        for _ in range(max_rounds):
            turn = self.converse(messages, system=system, tools=tools, temperature=temperature)
            accrue(turn)
            if turn.stop_reason != "tool_use":
                break
            if tool_executor is None:
                raise RuntimeError("model requested a tool but no tool_executor was provided")
            results = []
            for call in turn.tool_calls:
                out = tool_executor(call.name, call.input)
                gathered.append(out)
                results.append(
                    {"toolResult": {"toolUseId": call.tool_use_id, "content": [{"text": out}]}}
                )
            messages.append({"role": "user", "content": results})
            pending_tools = True
        else:
            # Round budget exhausted while still searching. Bedrock rejects a
            # tool-free call whose history holds tool blocks, so we make a fresh
            # standalone call: original question + the evidence already gathered,
            # no tools. Mirrors an engine capping search then generating.
            if pending_tools:
                forced = True
                digest = "\n\n---\n\n".join(gathered[-12:])
                fallback = (
                    f"{prompt}\n\nYou have already searched the web and found the "
                    f"following information:\n\n{digest}\n\nUsing the information above, "
                    "answer the question now. Do not search further."
                )
                turn = self.converse(
                    [{"role": "user", "content": [{"text": fallback}]}],
                    system=system,
                    tools=None,
                    temperature=temperature,
                )
                accrue(turn)

        return Conversation(
            final_text=turns[-1].text if turns else "",
            turns=turns,
            messages=messages,
            total_usage=usage,
            forced_answer=forced,
        )
