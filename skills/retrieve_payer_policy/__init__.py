from skills.common.io import execute
from skills.retrieve_payer_policy.tool import Input, Output, run_tool  # noqa: F401


def call(args):
    """call({...}) -> dict (same JSON the CLI prints)."""
    return execute("retrieve_payer_policy", Input.model_validate(args), run_tool).model_dump(mode="json")
