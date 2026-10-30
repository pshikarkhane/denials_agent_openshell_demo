import sys

from skills.common.io import cli
from skills.parse_denial_eob.tool import Input, run_tool

sys.exit(cli("parse_denial_eob", Input, run_tool))
