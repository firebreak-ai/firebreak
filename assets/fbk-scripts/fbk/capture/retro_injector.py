"""retro_injector — appends a provenance-marked metrics block to the retrospective.

Called by the state engine after a stage completes. Resolves the retrospective
path from os.getcwd() and the spec name; delegates block content to
report.stage_summary and section writing to retro.append_section.

All exceptions are swallowed so a failed injection never blocks the caller.
No stdout output — this can run inside a chokepoint stdout-redirect frame.
"""

import os


def inject_stage_metrics(spec: str, completed_stage: str) -> None:
    """Append a provenance-marked metrics block for completed_stage to the retrospective.

    Resolves the retrospective path as:
        <os.getcwd()>/ai-docs/<spec>/<spec>-retrospective.md

    The block is appended under a '## <STAGE> — metrics' heading (distinct from
    the plain '## <STAGE>' heading the skill uses for prose). Calling this twice
    for the same stage appends two separate marked blocks — each distinguished by
    its generated= timestamp.

    All exceptions are caught; on any internal failure this returns None without
    raising, so a failed injection never blocks the state transition that called it.

    Args:
        spec:            The spec name.
        completed_stage: The stage that just completed.

    Returns:
        None always.
    """
    try:
        from fbk import report
        from fbk import retro

        retro_path = os.path.join(
            os.getcwd(), "ai-docs", spec, f"{spec}-retrospective.md"
        )

        # Ensure the directory exists before appending (first injection creates it).
        os.makedirs(os.path.dirname(retro_path), exist_ok=True)

        content = report.stage_summary(spec, completed_stage)
        retro.append_section(retro_path, f"{completed_stage} — metrics", content)

    except Exception:
        return None
