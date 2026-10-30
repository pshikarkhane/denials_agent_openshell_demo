from skills.parse_denial_eob.tool import Input, Output, run_tool  # noqa: F401
from skills.common.io import execute


def call(args):
    """call({...}) -> dict (same JSON the CLI prints)."""
    return execute("parse_denial_eob", Input.model_validate(args), run_tool).model_dump(mode="json")
