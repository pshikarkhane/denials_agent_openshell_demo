from skills.common.io import execute
from skills.self_check.tool import Input, Output, run_tool  # noqa: F401


def call(args):
    """call({...}) -> dict (same JSON the CLI prints)."""
    return execute("self_check", Input.model_validate(args), run_tool).model_dump(mode="json")
