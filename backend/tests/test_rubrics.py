from mockinterview.agent.rubrics import CATEGORIES, all_rubrics, load_rubric


def test_load_each_rubric_has_4_dimensions():
    for c in CATEGORIES:
        r = load_rubric(c)
        assert r["category"] == c
        assert len(r["dimensions"]) == 4
        assert r["threshold_complete"] == 9


def test_all_rubrics_returns_5():
    assert len(all_rubrics()) == 5
