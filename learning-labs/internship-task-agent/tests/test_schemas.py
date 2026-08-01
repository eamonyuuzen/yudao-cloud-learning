import pytest
from pydantic import ValidationError

from internship_task_agent.schemas import QueryInternshipTasksArgs


def test_query_args_accept_valid_filters() -> None:
    args = QueryInternshipTasksArgs(
        title="用户",
        status=1,
        page_no=1,
        page_size=10,
    )

    assert args.status == 1
    assert args.page_size == 10


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("status", 99),
        ("page_no", 0),
        ("page_size", 0),
        ("page_size", 51),
        ("title", "x" * 201),
    ],
)
def test_query_args_reject_invalid_values(field: str, value: object) -> None:
    values = {"page_no": 1, "page_size": 10, field: value}

    with pytest.raises(ValidationError):
        QueryInternshipTasksArgs(**values)
