#!/usr/bin/env python3
"""
Consensus judge for Martian benchmark.

For each (golden, candidate) pair, runs N independent Anthropic-API judges
and takes a majority vote. Matches the consensus protocol used in prior
v0.4.0 benchmark runs (3x Sonnet via Claude Code subagents).

Output schema mirrors judge_active.json:
{
  "_metadata": {judge, model, judges_per_pair, aggregation, ...},
  "<pr_url>": {
    "1": {match: bool, votes: "N/N", best_candidate_idx: 0-based, reasoning: "..."},
    ...
  }
}

Plus a top-level "summary" key with TP/FP/FN per PR and aggregate.

Usage:
  ANTHROPIC_API_KEY=sk-... python3 judge_consensus.py \
    --input results/judge_input.json \
    --output results/judge_consensus_v040sd.json \
    --tool firebreak-v0.4.0-single-detector
"""

import argparse
import asyncio
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Error: pip install anthropic")
    sys.exit(1)

JUDGE_PROMPT = """You are evaluating AI code review tools.
Determine if the candidate issue matches the golden (expected) comment.

Golden Comment (the issue we're looking for):
{golden_comment}

Candidate Issue (from the tool's review):
{candidate}

Instructions:
- Determine if the candidate identifies the SAME underlying issue as the golden comment
- Accept semantic matches - different wording is fine if it's the same problem
- Focus on whether they point to the same bug, concern, or code issue

Respond with ONLY a JSON object:
{{"reasoning": "brief explanation", "match": true/false, "confidence": 0.0-1.0}}"""

DEFAULT_MODEL = "claude-sonnet-4-6"
TIMEOUT = 30
DEFAULT_JUDGES = 3
PAIR_BATCH_SIZE = 8  # parallel pairs in flight (each pair runs N judges)


class ConsensusJudge:
    def __init__(self, model: str, judges_per_pair: int):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        self.judges_per_pair = judges_per_pair
        # Different temperatures per judge so they don't collapse to identical output
        self.temperatures = [0.0, 0.2, 0.4][:judges_per_pair]
        if len(self.temperatures) < judges_per_pair:
            self.temperatures.extend([0.5] * (judges_per_pair - len(self.temperatures)))

    async def _single_call(self, prompt: str, temperature: float) -> dict:
        for attempt in range(3):
            try:
                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self.model,
                        max_tokens=256,
                        temperature=temperature,
                        system="You are a precise code review evaluator. Always respond with valid JSON.",
                        messages=[{"role": "user", "content": prompt}],
                    ),
                    timeout=TIMEOUT,
                )
                content = response.content[0].text.strip()
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                return json.loads(content)
            except asyncio.TimeoutError:
                if attempt == 2:
                    return {"error": f"Timed out after {TIMEOUT}s"}
                await asyncio.sleep(2 ** attempt)
            except json.JSONDecodeError:
                if attempt == 2:
                    return {"error": "JSON parse failed"}
                await asyncio.sleep(1)
            except Exception as e:
                msg = str(e)
                # Retry on overload, backoff
                if "overload" in msg.lower() or "529" in msg:
                    await asyncio.sleep(5 * (attempt + 1))
                    if attempt == 2:
                        return {"error": msg}
                    continue
                if attempt == 2:
                    return {"error": msg}
                await asyncio.sleep(2 ** attempt)
        return {"error": "Max retries exceeded"}

    async def judge_pair(self, golden: str, candidate: str) -> dict:
        prompt = JUDGE_PROMPT.format(golden_comment=golden, candidate=candidate)
        results = await asyncio.gather(*[
            self._single_call(prompt, t) for t in self.temperatures
        ])
        votes = []
        confidences = []
        reasonings = []
        errors = []
        for r in results:
            if r.get("error"):
                errors.append(r["error"])
                continue
            votes.append(bool(r.get("match", False)))
            confidences.append(float(r.get("confidence", 0.0)))
            reasonings.append(r.get("reasoning", ""))

        if not votes:
            return {"match": False, "votes": "0/0", "errors": errors}

        match_count = sum(votes)
        consensus_match = match_count > len(votes) / 2
        return {
            "match": consensus_match,
            "votes": f"{match_count}/{len(votes)}",
            "vote_detail": votes,
            "confidence": (sum(confidences) / len(confidences)) if confidences else 0.0,
            "reasoning": reasonings[0] if reasonings else "",
            "errors": errors if errors else None,
        }


async def evaluate_pr(judge: ConsensusJudge, entry: dict) -> dict:
    """Evaluate one PR's candidates against golden comments."""
    goldens = entry["golden_comments"]
    candidates = entry["candidates"]
    severities = entry.get("golden_severities", [None] * len(goldens))

    if not goldens:
        return {"skipped": True, "reason": "No golden comments"}
    if not candidates:
        return {
            "skipped": False,
            "tp": 0, "fp": 0, "fn": len(goldens),
            "true_positives": [],
            "false_positives": [],
            "false_negatives": [{"golden_index": i + 1, "golden": g, "severity": s}
                               for i, (g, s) in enumerate(zip(goldens, severities))],
            "judgments": {},
        }

    # Build all (golden, candidate) tasks
    tasks = []
    task_keys = []
    for gi, golden in enumerate(goldens):
        for ci, candidate in enumerate(candidates):
            tasks.append((golden, candidate))
            task_keys.append((gi, ci))

    # Process in batches to limit concurrent in-flight pairs
    pair_results = {}
    for i in range(0, len(tasks), PAIR_BATCH_SIZE):
        batch = tasks[i:i + PAIR_BATCH_SIZE]
        batch_keys = task_keys[i:i + PAIR_BATCH_SIZE]
        results = await asyncio.gather(*[judge.judge_pair(g, c) for g, c in batch])
        for k, r in zip(batch_keys, results):
            pair_results[k] = r
        if i + PAIR_BATCH_SIZE < len(tasks):
            await asyncio.sleep(0.3)

    # Per-golden: find best matching candidate (consensus match + highest confidence)
    judgments = {}
    candidate_matched = [False] * len(candidates)
    true_positives = []
    false_negatives = []

    for gi in range(len(goldens)):
        best_ci = None
        best_conf = -1.0
        best_result = None
        for ci in range(len(candidates)):
            r = pair_results.get((gi, ci), {})
            if r.get("match") and r.get("confidence", 0.0) > best_conf:
                best_conf = r["confidence"]
                best_ci = ci
                best_result = r

        golden_key = str(gi + 1)
        if best_ci is not None:
            judgments[golden_key] = {
                "match": True,
                "candidate_index": best_ci + 1,  # 1-based for parity with judge_active.json
                "votes": best_result["votes"],
                "confidence": best_result["confidence"],
                "reasoning": best_result.get("reasoning", ""),
            }
            candidate_matched[best_ci] = True
            true_positives.append({
                "golden_index": gi + 1,
                "candidate_index": best_ci + 1,
                "severity": severities[gi] if gi < len(severities) else None,
                "votes": best_result["votes"],
            })
        else:
            judgments[golden_key] = {"match": False, "candidate_index": None}
            false_negatives.append({
                "golden_index": gi + 1,
                "golden": goldens[gi],
                "severity": severities[gi] if gi < len(severities) else None,
            })

    false_positives = [
        {"candidate_index": ci + 1}
        for ci, matched in enumerate(candidate_matched) if not matched
    ]

    return {
        "skipped": False,
        "tp": len(true_positives),
        "fp": len(false_positives),
        "fn": len(false_negatives),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "judgments": judgments,
    }


async def main():
    parser = argparse.ArgumentParser(description="Consensus judge for Martian benchmark")
    parser.add_argument("--input", required=True, help="judge_input.json from extract_candidates.py")
    parser.add_argument("--output", required=True, help="Output JSON path")
    parser.add_argument("--tool", default="firebreak", help="Tool name for metadata")
    parser.add_argument("--judges", type=int, default=DEFAULT_JUDGES)
    parser.add_argument("--model", default=os.environ.get("JUDGE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--limit", type=int, help="Limit number of PRs")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    with open(args.input) as f:
        entries = json.load(f)
    if args.limit:
        entries = entries[: args.limit]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume support: load existing output and skip done PRs unless --force
    state = {}
    if output_path.exists() and not args.force:
        with open(output_path) as f:
            state = json.load(f)

    judge = ConsensusJudge(args.model, args.judges)
    print(f"Judge model: {args.model}, judges per pair: {args.judges}")
    print(f"PRs to evaluate: {len(entries)}")

    for i, entry in enumerate(entries, start=1):
        pr_url = entry["pr_url"]
        if pr_url in state and not args.force:
            r = state[pr_url]
            print(f"[{i}/{len(entries)}] {entry['instance_id']}  SKIP (cached)  TP={r.get('tp',0)} FP={r.get('fp',0)} FN={r.get('fn',0)}")
            continue
        print(f"[{i}/{len(entries)}] {entry['instance_id']}  goldens={entry['golden_count']} candidates={entry['candidate_count']}")
        result = await evaluate_pr(judge, entry)
        result["pr_url"] = pr_url
        result["instance_id"] = entry["instance_id"]
        result["source_repo"] = entry.get("source_repo")
        state[pr_url] = result

        # Persist after each PR (resume safety)
        out = {
            "_metadata": {
                "judge": f"consensus ({args.judges}x {args.model}, majority vote)",
                "model": args.model,
                "judges_per_pair": args.judges,
                "aggregation": "majority vote",
                "tool": args.tool,
                "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "input": str(args.input),
                "notes": "Golden index and candidate index are 1-based. null candidate_index means no match.",
            },
            **state,
        }
        # Aggregate summary
        evaluated = [r for r in state.values() if not r.get("skipped")]
        tp = sum(r.get("tp", 0) for r in evaluated)
        fp = sum(r.get("fp", 0) for r in evaluated)
        fn = sum(r.get("fn", 0) for r in evaluated)
        p = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        r_ = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * p * r_ / (p + r_) if (p + r_) > 0 else 0.0
        out["_summary"] = {
            "evaluated_prs": len(evaluated),
            "tp": tp, "fp": fp, "fn": fn,
            "precision": round(p, 4),
            "recall": round(r_, 4),
            "f1": round(f1, 4),
        }

        with open(output_path, "w") as f:
            json.dump(out, f, indent=2, ensure_ascii=False)

        print(f"     TP={result['tp']} FP={result['fp']} FN={result['fn']}  agg P={p:.1%} R={r_:.1%} F1={f1:.1%}")

    print(f"\nResults: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
