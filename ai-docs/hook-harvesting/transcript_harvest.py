#!/usr/bin/env python3
"""Transcript harvester — deterministic metrics from Claude Code session JSONL.

Reads session transcripts (and their subagent transcripts) and emits per-session
and per-agent metrics: tokens by type, turns, tool calls by tool, tool errors,
models used, wall-clock span. No live instrumentation required — this parses
what the harness already records.

Usage:
  transcript_harvest.py <transcript.jsonl> [...]   harvest specific files
  transcript_harvest.py --project <dir>            harvest newest session in a
                                                   Claude project dir
                                                   (e.g. ~/.claude/projects/-opt-code)
  transcript_harvest.py --project <dir> --all      harvest every session
  --json                                           machine-readable output

Built 2026-06-10 against observed record structure (Claude Code v2.x):
- record types seen: user / assistant / system / attachment + metadata records
  (mode, permission-mode, file-history-snapshot, ai-title, last-prompt)
- assistant records: .message.usage {input_tokens, output_tokens,
  cache_read_input_tokens, cache_creation_input_tokens}, .message.model,
  .timestamp, .isSidechain
- tool_use blocks live in assistant .message.content[]; tool results arrive in
  user records (.toolUseResult / tool_result content blocks with is_error)
- system records log hook executions (hookCount, hookErrors, durationMs)
- subagent transcripts: <project>/<session-id>/subagents/agent-<id>.jsonl
  with sibling agent-<id>.meta.json
Token costs are intentionally NOT computed (no pricing table baked in —
multiply tokens by current pricing externally).
"""

import argparse
import datetime
import glob
import json
import os
import sys
from collections import Counter, defaultdict


def parse_ts(s):
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def harvest_file(path):
    """Harvest one transcript JSONL into a metrics dict."""
    m = {
        "path": path,
        "record_types": Counter(),
        "turns": 0,  # assistant API responses
        "sidechain_turns": 0,
        "tokens": Counter(),  # input/output/cache_read/cache_creation
        "tokens_by_model": defaultdict(Counter),
        "tool_calls": Counter(),  # by tool name
        "tool_errors": Counter(),  # by tool name
        "hook_executions": 0,
        "hook_errors": 0,
        "hook_duration_ms": 0,
        "user_prompts": 0,  # human messages (non-meta, non-tool-result)
        "first_ts": None,
        "last_ts": None,
    }
    # tool_use id -> name, so errors in later tool_result blocks attribute correctly
    tool_names_by_id = {}

    try:
        f = open(path, encoding="utf-8", errors="replace")
    except OSError as e:
        m["error"] = str(e)
        return m

    with f:
        for line in f:
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                m["record_types"]["_unparseable"] += 1
                continue

            rtype = rec.get("type", "?")
            m["record_types"][rtype] += 1

            ts = parse_ts(rec.get("timestamp", "")) if rec.get("timestamp") else None
            if ts:
                if m["first_ts"] is None or ts < m["first_ts"]:
                    m["first_ts"] = ts
                if m["last_ts"] is None or ts > m["last_ts"]:
                    m["last_ts"] = ts

            msg = rec.get("message")

            if rtype == "assistant" and isinstance(msg, dict):
                if rec.get("isSidechain"):
                    m["sidechain_turns"] += 1
                else:
                    m["turns"] += 1
                usage = msg.get("usage") or {}
                model = msg.get("model", "unknown")
                for src_key, dst_key in (
                    ("input_tokens", "input"),
                    ("output_tokens", "output"),
                    ("cache_read_input_tokens", "cache_read"),
                    ("cache_creation_input_tokens", "cache_creation"),
                ):
                    v = usage.get(src_key) or 0
                    m["tokens"][dst_key] += v
                    m["tokens_by_model"][model][dst_key] += v
                content = msg.get("content")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            name = block.get("name", "?")
                            m["tool_calls"][name] += 1
                            if block.get("id"):
                                tool_names_by_id[block["id"]] = name

            elif rtype == "user" and isinstance(msg, dict):
                content = msg.get("content")
                saw_tool_result = False
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "tool_result":
                            saw_tool_result = True
                            if block.get("is_error"):
                                name = tool_names_by_id.get(block.get("tool_use_id"), "?")
                                m["tool_errors"][name] += 1
                if not saw_tool_result and not rec.get("isMeta") and not rec.get("isSidechain"):
                    m["user_prompts"] += 1

            elif rtype == "system":
                hooks_n = rec.get("hookCount")
                if hooks_n:
                    m["hook_executions"] += hooks_n
                    errs = rec.get("hookErrors")
                    if errs:
                        m["hook_errors"] += len(errs) if isinstance(errs, list) else 1
                    m["hook_duration_ms"] += rec.get("durationMs") or 0

    if m["first_ts"] and m["last_ts"]:
        m["wall_clock_s"] = round((m["last_ts"] - m["first_ts"]).total_seconds(), 1)
    return m


def harvest_session(transcript_path):
    """Harvest a main transcript plus any subagent transcripts beside it."""
    session = {"main": harvest_file(transcript_path), "subagents": []}
    session_id = os.path.splitext(os.path.basename(transcript_path))[0]
    sub_dir = os.path.join(os.path.dirname(transcript_path), session_id, "subagents")
    for sub in sorted(glob.glob(os.path.join(sub_dir, "agent-*.jsonl"))):
        sm = harvest_file(sub)
        meta_path = sub.replace(".jsonl", ".meta.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as mf:
                    sm["meta"] = json.load(mf)
            except Exception:
                pass
        session["subagents"].append(sm)
    return session


def fmt_counter(c, top=None):
    items = c.most_common(top) if top else sorted(c.items())
    return ", ".join(f"{k}={v}" for k, v in items) or "-"


def render(session):
    out = []
    for label, m in [("MAIN", session["main"])] + [
        (f"SUBAGENT {os.path.basename(s['path'])}", s) for s in session["subagents"]
    ]:
        out.append(f"== {label} ==")
        if m.get("error"):
            out.append(f"  error: {m['error']}")
            continue
        meta = m.get("meta") or {}
        if meta:
            desc = meta.get("description") or meta.get("agentType") or ""
            if desc:
                out.append(f"  agent: {desc}")
        t = m["tokens"]
        out.append(
            f"  turns={m['turns']} (sidechain={m['sidechain_turns']})  "
            f"user_prompts={m['user_prompts']}  wall_clock_s={m.get('wall_clock_s', '-')}"
        )
        out.append(
            f"  tokens: in={t['input']} out={t['output']} "
            f"cache_read={t['cache_read']} cache_create={t['cache_creation']}"
        )
        for model, mt in m["tokens_by_model"].items():
            out.append(f"    [{model}] in={mt['input']} out={mt['output']} cache_read={mt['cache_read']}")
        out.append(f"  tool_calls: {fmt_counter(m['tool_calls'])}")
        if m["tool_errors"]:
            out.append(f"  tool_errors: {fmt_counter(m['tool_errors'])}")
        if m["hook_executions"]:
            out.append(
                f"  hooks: executions={m['hook_executions']} errors={m['hook_errors']} "
                f"total_ms={m['hook_duration_ms']}"
            )
    return "\n".join(out)


def jsonable(obj):
    if isinstance(obj, (Counter, defaultdict, dict)):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [jsonable(v) for v in obj]
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    return obj


def main():
    ap = argparse.ArgumentParser(description="Harvest metrics from Claude Code transcripts")
    ap.add_argument("files", nargs="*", help="transcript .jsonl paths")
    ap.add_argument("--project", help="Claude project dir (harvests newest session)")
    ap.add_argument("--all", action="store_true", help="with --project: every session")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    targets = list(args.files)
    if args.project:
        candidates = sorted(
            glob.glob(os.path.join(os.path.expanduser(args.project), "*.jsonl")),
            key=os.path.getmtime,
            reverse=True,
        )
        targets.extend(candidates if args.all else candidates[:1])
    if not targets:
        ap.error("no transcripts given (pass files or --project)")

    sessions = [harvest_session(t) for t in targets]
    if args.json:
        print(json.dumps(jsonable(sessions), indent=1, default=str))
    else:
        for s in sessions:
            print(render(s))
            print()


if __name__ == "__main__":
    main()
