import pytest

from resume_taylor.pipeline.runtime import WARNINGS


@pytest.fixture(autouse=True)
def _clear_warnings():
    WARNINGS.clear()
    yield
    WARNINGS.clear()


@pytest.fixture
def bank():
    return {
        "F001": {"id": "F001", "employer": "Acme", "text": "Saved $300k per year with MMM.", "metrics": ["$300k"]},
        "F002": {"id": "F002", "employer": "Globex", "text": "Built a churn model.", "metrics": []},
        "F003": {"id": "F003", "employer": "unassigned", "text": "Led a POC.", "metrics": []},
        "F004": {"id": "F004", "employer": "general", "text": "Python and SQL.", "metrics": []},
    }
