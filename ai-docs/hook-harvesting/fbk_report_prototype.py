#!/usr/bin/env python3
"""Prototype of `fbk report` — joins three deterministic streams into one table.

Streams:
  1. Hook capture   (.fbk-capture/events.jsonl)         — process events, stage-stamped
  2. State engine   (.claude/automation/state/*.json)   — stage transitions + durations + parks
  3. Transcripts    (~/.claude/projects/<slug>/*.jsonl) — tokens/turns via transcript_harvest

Output: per-spec, per-stage metrics table + session-level process metrics.
This is a porting candidate for Firebreak's `fbk report` command, not the final
implementation — see firebreak-instrumentation-brief.md.

Usage: fbk_report_prototype.py [--project-root DIR] [--transcripts DIR] [--json]
"""

import argparse
import datetime
import glob
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from transcript_harvest import harvest_session  # noqa: E402


def parse_ts(s):
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def load_events(root):
    path = os.path.join(root, ".fbk-capture", "events.jsonl")
    if not os.path.exists(path):
        return []
    out = []
    with open(path) as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def stage_durations(root):
    """Per-spec stage durations from the state engine's stage_timestamps."""
    result = {}
    for sf in glob.glob(os.path.join(root, ".claude", "automation", "state", "*.json")):
        try:
            with open(sf) as f:
                state = json.load(f)
        except Exception:
            continue
        ts = {k: parse_ts(v) for k, v in (state.get("stage_timestamps") or {}).items()}
        ordered = sorted((v, k) for k, v in ts.items() if v)
        durations = []
        for i, (t, stage) in enumerate(ordered):
            end = ordered[i + 1][0] if i + 1 < len(ordered) else None
            durations.append({
                "stage": stage,
                "entered": t.isoformat(),
                "duration_s": round((end - t).total_seconds(), 1) if end else None,
            })
        result[state.get("spec_name", os.path.basename(sf))] = {
            "current_state": state.get("current_state"),
            "stages": durations,
            "parks": state.get("error_history") or [],
        }
    return result


def process_metrics(events):
    """Session-level and per-stage process metrics from hook capture."""
    per_stage = defaultdict(lambda: {
        "tool_calls": Counter(), "tool_errors": Counter(),
        "edits_by_file": Counter(), "subagent_stops": 0, "events": 0,
    })
    session = {
        "user_prompts": 0, "stops": 0, "compactions": 0,
        "permission_requests": 0, "tool_failures": Counter(),
        "subagents": [],
    }
    for e in events:
        fbk = e.get("fbk") or {}
        key = (fbk.get("spec") or "-", fbk.get("stage") or "-")
        s = per_stage[key]
        s["events"] += 1
        ev, p = e["event"], e.get("payload", {})
        if ev == "PostToolUse":
            tool = p.get("tool_name", "?")
            s["tool_calls"][tool] += 1
            if tool in ("Edit", "Write") and isinstance(p.get("tool_input"), dict):
                fp = p["tool_input"].get("file_path")
                if fp:
                    s["edits_by_file"][fp] += 1
        elif ev == "PostToolUseFailure":
            tool = p.get("tool_name", "?")
            s["tool_errors"][tool] += 1
            session["tool_failures"][tool] += 1
        elif ev == "UserPromptSubmit":
            session["user_prompts"] += 1
        elif ev == "Stop":
            session["stops"] += 1
        elif ev == "PreCompact":
            session["compactions"] += 1
        elif ev == "PermissionRequest":
            session["permission_requests"] += 1
        elif ev == "SubagentStop":
            s["subagent_stops"] += 1
            session["subagents"].append({
                "agent_id": e.get("agent_id"),
                "agent_type": e.get("agent_type"),
                "transcript": p.get("agent_transcript_path"),
                "result_preview": (p.get("last_assistant_message") or "")[:120],
                "stage": key,
            })
    # thrash: files edited more than twice within one stage
    for s in per_stage.values():
        s["thrash_files"] = {f: n for f, n in s["edits_by_file"].items() if n > 2}
    return session, per_stage


def token_metrics(transcript_path):
    if not transcript_path or not os.path.exists(transcript_path):
        return None
    h = harvest_session(transcript_path)
    m = h["main"]
    return {
        "turns": m["turns"],
        "tokens": dict(m["tokens"]),
        "wall_clock_s": m.get("wall_clock_s"),
        "subagent_count": len(h["subagents"]),
        "subagent_tokens": {
            os.path.basename(s["path"]): dict(s["tokens"]) for s in h["subagents"]
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project-root", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    root = args.project_root

    events = load_events(root)
    session, per_stage = process_metrics(events)
    states = stage_durations(root)
    # transcript path: take it from the most recent captured event (hooks deliver it)
    tpath = next((e["payload"].get("transcript_path") for e in reversed(events)
                  if e.get("payload", {}).get("transcript_path")), None)
    tokens = token_metrics(tpath)

    report = {
        "events_captured": len(events),
        "session_process": session,
        "per_stage": {f"{k[0]}/{k[1]}": {
            "tool_calls": dict(v["tool_calls"]), "tool_errors": dict(v["tool_errors"]),
            "thrash_files": v["thrash_files"], "subagent_stops": v["subagent_stops"],
            "events": v["events"],
        } for k, v in per_stage.items()},
        "specs": states,
        "tokens": tokens,
    }

    if args.json:
        print(json.dumps(report, indent=1, default=str))
        return

    print(f"events captured: {report['events_captured']}")
    print(f"user prompts: {session['user_prompts']}  turns(Stop): {session['stops']}  "
          f"compactions: {session['compactions']}  tool failures: {dict(session['tool_failures'])}")
    if tokens:
        t = tokens["tokens"]
        print(f"tokens: in={t.get('input', 0)} out={t.get('output', 0)} "
              f"cache_read={t.get('cache_read', 0)}  turns={tokens['turns']}  "
              f"subagents={tokens['subagent_count']}")
    print("\nper stage (spec/stage):")
    for label, v in report["per_stage"].items():
        print(f"  {label:<40} events={v['events']:<4} tools={v['tool_calls']} "
              f"errors={v['tool_errors']} thrash={v['thrash_files']}")
    print("\nspecs (state engine):")
    for spec, st in states.items():
        print(f"  {spec}: now={st['current_state']}, parks={len(st['parks'])}")
        for d in st["stages"]:
            dur = f"{d['duration_s']}s" if d["duration_s"] is not None else "(current)"
            print(f"    {d['stage']:<16} {dur}")
    print("\nsubagents:")
    for sa in session["subagents"]:
        print(f"  [{sa['agent_type']}] {sa['agent_id']} stage={sa['stage']}")
        print(f"    result: {sa['result_preview']}")


if __name__ == "__main__":
    main()
