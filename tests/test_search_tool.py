from aeo.search_tool import ControlledSearchIndex, FixedResultTool, SearchDoc


def make_index():
    docs = [
        SearchDoc("d1", "About Harrowfield & Vance Realty", "https://x.com/1",
                  "Boutique brokerage in Pasadena founded in 2019 by Elena Marchetti."),
        SearchDoc("d2", "Redfin Company Profile", "https://x.com/2",
                  "Redfin is a technology-powered real estate brokerage."),
        SearchDoc("d3", "Choosing a brokerage", "https://x.com/3",
                  "Compare brokerages on commission structure and marketing."),
    ]
    return ControlledSearchIndex(docs, k=2)


def test_search_ranks_entity_doc_first():
    index = make_index()
    hits = index.search("Harrowfield Vance Realty Pasadena")
    assert hits and hits[0].doc_id == "d1"


def test_query_log_records_served_docs():
    index = make_index()
    index.search("Redfin brokerage")
    assert index.query_log[0].query == "Redfin brokerage"
    assert "d2" in index.query_log[0].returned_doc_ids


def test_executor_formats_results():
    index = make_index()
    out = index.executor("web_search", {"query": "Redfin"})
    assert "Title: Redfin Company Profile" in out
    assert "URL: https://x.com/2" in out


def test_executor_no_hits():
    index = make_index()
    assert index.executor("web_search", {"query": "zzqx unrelated"}) == "No results found."


def test_fixed_result_tool_ignores_query_and_preserves_order():
    docs = [
        SearchDoc("d1", "First", "https://x/1", "alpha"),
        SearchDoc("d2", "Second", "https://x/2", "beta"),
    ]
    tool = FixedResultTool(docs)
    out1 = tool.executor("web_search", {"query": "anything"})
    out2 = tool.executor("web_search", {"query": "totally different"})
    assert out1 == out2  # query-independent
    assert out1.index("Title: First") < out1.index("Title: Second")  # order preserved
    assert tool.query_log == ["anything", "totally different"]
