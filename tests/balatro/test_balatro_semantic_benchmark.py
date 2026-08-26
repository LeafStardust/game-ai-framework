from games.balatro.red_white_semantic_cases import RED_WHITE_SEMANTIC_CASES
from games.balatro.semantic_benchmark import run_semantic_benchmark


def test_red_white_semantic_benchmark_cases_have_unique_ids_and_pass():
    report = run_semantic_benchmark(RED_WHITE_SEMANTIC_CASES)

    assert report.total == len(RED_WHITE_SEMANTIC_CASES)
    assert report.total >= 6
    assert not report.failed, "\n" + report.render()


def test_red_white_semantic_benchmark_reports_category_scores():
    report = run_semantic_benchmark(RED_WHITE_SEMANTIC_CASES)
    scores = {score.category: score for score in report.categories}

    assert "D1_SURVIVAL" in scores
    assert "SHOP_SURVIVAL" in scores
    assert "BUILD_COHERENCE" in scores
    assert all(score.passed == score.total for score in scores.values())
