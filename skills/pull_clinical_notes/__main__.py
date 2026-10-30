import sys

from skills.common.io import cli
from skills.pull_clinical_notes.tool import Input, run_tool

sys.exit(cli("pull_clinical_notes", Input, run_tool))
