from skills.common.io import execute
from skills.draft_deliverable.tool import Input, Output, run_tool  # noqa: F401


def call(args):
    """call({...}) -> dict (same JSON the CLI prints)."""
    return execute("draft_deliverable", Input.model_validate(args), run_tool).model_dump(mode="json")
