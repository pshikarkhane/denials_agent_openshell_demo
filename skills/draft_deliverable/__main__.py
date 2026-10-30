import sys

from skills.common.io import cli
from skills.draft_deliverable.tool import Input, run_tool

sys.exit(cli("draft_deliverable", Input, run_tool))
