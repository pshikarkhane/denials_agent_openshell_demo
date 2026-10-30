"""Parse the model's final answer: <<<DELIVERABLE>>> ... <<<DECISION>>> ... <<<END>>>."""
import re

# Tolerant of a slipped bracket count: the model sometimes writes <<<DELIVERABLE>> (two closing brackets) instead of three.
PATTERN = re.compile(r"<{2,3}\s*DELIVERABLE\s*>{2,3}\s*(.*?)\s*<{2,3}\s*DECISION\s*>{2,3}\s*(.*?)\s*(?:<{2,3}\s*END\s*>{2,3}|\Z)", re.S)


def parse_final(text):
    """-> (deliverable_md, decision_json_text) or None."""
    if not text:
        return None
    m = PATTERN.search(text)
    if not m or not m.group(1).strip() or not m.group(2).strip():
        return None
    dec = re.sub(r"^```(?:json)?\s*|\s*```$", "", m.group(2).strip())
    return m.group(1).strip() + "\n", dec + "\n"
