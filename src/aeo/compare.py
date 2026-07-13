"""Rank-comparison metric for Experiment 2 (the curation rate).

Kendall's tau between the search results' presented order and the model's
ranking. tau ~ 1 means the model echoes the presented order (AEO reduces to
SEO); low tau means the model reorders on content (genuine curation).
"""

from __future__ import annotations


def kendall_tau(rank_a: list[str], rank_b: list[str]) -> float | None:
    """Kendall's tau-b over items ranked by BOTH lists.

    Returns None if fewer than two common items (tau undefined). Items are
    compared by their position in each list (index 0 = best).
    """
    common = [x for x in rank_a if x in set(rank_b)]
    if len(common) < 2:
        return None
    pos_a = {x: i for i, x in enumerate(rank_a)}
    pos_b = {x: i for i, x in enumerate(rank_b)}
    concordant = discordant = 0
    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            x, y = common[i], common[j]
            s = (pos_a[x] - pos_a[y]) * (pos_b[x] - pos_b[y])
            if s > 0:
                concordant += 1
            elif s < 0:
                discordant += 1
    n = concordant + discordant
    return (concordant - discordant) / n if n else None
