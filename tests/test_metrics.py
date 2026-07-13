from aeo.metrics import abstains, adopted_facts, mentions


def test_mentions_normalizes_punctuation():
    assert mentions("I recommend Harrowfield & Vance Realty.", "Harrowfield & Vance Realty")
    assert mentions("Try Angie's List for that.", "Angi", aliases=["Angie's List"])
    assert not mentions("No relevant firms here.", "Redfin")


def test_adopted_facts():
    answer = "The firm was founded in 2019 by Elena Marchetti and has 14 agents."
    hits = adopted_facts(answer, ["founded in 2019", "Marchetti", "$89 per month"])
    assert hits["founded in 2019"] and hits["Marchetti"]
    assert not hits["$89 per month"]


def test_abstains_patterns():
    assert abstains("I don't have specific information about that company.")
    assert abstains("I'm not familiar with Tidecrest Home Concierge.")
    assert not abstains("Redfin was founded in 2004 in Seattle.")
