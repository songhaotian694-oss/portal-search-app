from app.api.analytics import relationships, summarize


def test_local_analytics_counts_records_and_relationships():
    rows = [
        {"graduation_year": "2024届", "major": "计算机", "city": "北京", "position": "信息岗", "needs_review": 0},
        {"graduation_year": "2024届", "major": "计算机", "city": "北京", "position": "信息岗", "needs_review": 1},
        {"graduation_year": "待人工核对", "major": "法学", "city": "天津", "position": "综合岗", "needs_review": 1},
    ]
    summary = summarize(rows)
    assert summary["total"] == 3
    assert summary["needsReview"] == 2
    assert summary["cities"][0] == ["北京", 2]
    assert summary["years"] == [["2024", 2]]
    graph = relationships(rows, ["major", "city", "position"])
    assert {link["count"] for link in graph["links"]} == {1, 2}
    assert sum(link["count"] for link in graph["links"]) == 2 * len(rows)
