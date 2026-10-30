import sys

from skills.common.io import cli
from skills.assess_appealability.tool import Input, run_tool

sys.exit(cli("assess_appealability", Input, run_tool))
