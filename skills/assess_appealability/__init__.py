from skills.common.io import execute
from skills.assess_appealability.tool import Input, Output, run_tool  # noqa: F401


def call(args):
    """call({...}) -> dict (same JSON the CLI prints)."""
    return execute("assess_appealability", Input.model_validate(args), run_tool).model_dump(mode="json")
