"""Launch-prompt descriptor parser for the observability substrate.

Extracts cardinality, stance, and optional asset_bundle from the
``<!--fbk-attr {json}-->`` block prepended to each agent's launch (first)
prompt.  Only the FIRST matching block is considered — any later block
(e.g. one forged by the agent itself) is silently ignored.

When no block is present, or the captured JSON is malformed, the function
returns an all-null descriptor with ``attribution_absent=True`` and never
raises.

Depends only on ``json`` and ``re`` from the standard library.
"""

import json
import re

_ATTR_RE = re.compile(r"<!--fbk-attr (\{.*?\})-->", re.DOTALL)


def parse_attribution(first_message_text: str) -> dict:
    """Parse the launch-prompt attribution descriptor from *first_message_text*.

    Parameters
    ----------
    first_message_text:
        The full text of the agent's first (launch) message.

    Returns
    -------
    dict with keys:
        ``cardinality``        – ``"single"`` / ``"fan-out"`` / ``None``
        ``stance``             – ``"collaborative"`` / ``"adversarial"`` / ``None``
        ``attribution_absent`` – ``False`` when a valid block was found, else ``True``
        ``asset_bundle``       – present only when the JSON contained that key
    """
    _absent = {"cardinality": None, "stance": None, "attribution_absent": True}

    match = _ATTR_RE.search(first_message_text)
    if match is None:
        return _absent

    try:
        parsed = json.loads(match.group(1))
    except (json.JSONDecodeError, ValueError):
        return _absent

    result = {
        "cardinality": parsed.get("cardinality"),
        "stance": parsed.get("stance"),
        "attribution_absent": False,
    }

    if "asset_bundle" in parsed:
        result["asset_bundle"] = parsed["asset_bundle"]

    return result
