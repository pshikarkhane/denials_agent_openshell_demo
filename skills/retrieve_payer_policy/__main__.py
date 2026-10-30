import sys

from skills.common.io import cli
from skills.retrieve_payer_policy.tool import Input, run_tool

sys.exit(cli("retrieve_payer_policy", Input, run_tool))
