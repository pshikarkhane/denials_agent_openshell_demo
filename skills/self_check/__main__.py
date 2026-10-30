import sys

from skills.common.io import cli
from skills.self_check.tool import Input, run_tool

sys.exit(cli("self_check", Input, run_tool))
