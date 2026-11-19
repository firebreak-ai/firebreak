#!/usr/bin/env bash
# Settings that keep the operator's instruction files out of a benchmark session, as one JSON line for claude's
# --settings: clean-settings.sh <work-folder> [settings.json]
# Claude Code loads CLAUDE.md, CLAUDE.local.md, .claude/CLAUDE.md and .claude/rules/ of every folder above a session's
# work folder as project instructions, whatever --setting-sources says about user settings. The work folders are under
# the operator's home, so ~/.claude/CLAUDE.md came in that way, and its import line led sessions to open the file it
# names. The claudeMdExcludes setting lists those files for every folder above <work-folder>; the work folder's own
# instruction files (a workflow's .claude) stay loaded. The keys of [settings.json] are kept.
set -euo pipefail
d=$(dirname "$(realpath -m "$1")"); x=()
while :; do p=${d%/}; x+=("$p/CLAUDE.md" "$p/CLAUDE.local.md" "$p/.claude/CLAUDE.md" "$p/.claude/rules/**"); [ "$d" = / ] && break; d=$(dirname "$d"); done
{ if [ -n "${2:-}" ]; then cat "$2"; else echo '{}'; fi; } | jq -c '. + {claudeMdExcludes: $ARGS.positional}' --args "${x[@]}"
