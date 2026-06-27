#!/usr/bin/env python3
"""
LLM judge for Martian benchmark using Anthropic API directly.

Adapted from the benchmark's step3_judge_comments.py to use Anthropic credits
instead of the Martian router API. Evaluates Firebreak (or any tool) against
golden comments and computes precision/recall/F1.

Prerequisites:
  pip install anthropic

Usage:
  ANTHROPIC_API_KEY=sk-ant-... python3 judge_anthropic.py [--tool firebreak] [--limit N]

Environment:
  ANTHROPIC_API_KEY  - Anthropic API key
  JUDGE_MODEL        - Model to use (default: claude-sonnet-4-5-20250929)
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path

try:
    import anthropic
except ImportError:
    print("Error: pip install anthropic")
    sys.exit(1)

BENCHMARK_DATA = Path("/tmp/code-review-benchmark/offline/results/benchmark_data.json")
RESULTS_DIR = Path(__file__).parent / "results"
BATCH_SIZE = 10  # Conservative for Anthropic rate limits
TIMEOUT = 30

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

# Reuse the same prompt as the Martian benchmark for comparability.
# The prompt is from step3_judge_comments.py in the benchmark repo.


class AnthropicJudge:
    def __init__(self, model: str):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable required")
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model
        print(f"Judge model: {self.model}")

    async def match_comment(self, golden_comment: str, candidate: str) -> dict:
        prompt = JUDGE_PROMPT.format(golden_comment=golden_comment, candidate=candidate)
        for attempt in range(3):
            try:
                response = await asyncio.wait_for(
                    self.client.messages.create(
                        model=self.model,
                        max_tokens=256,
                        temperature=0.0,
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
                if attempt == 2:
                    return {"error": str(e)}
                await asyncio.sleep(2 ** attempt)
        return {"error": "Max retries exceeded"}


async def evaluate_review(
    judge: AnthropicJudge,
    golden_comments: list[dict],
    candidates: list[str],
) -> dict:
    """Evaluate candidates against golden comments."""
    if not golden_comments:
        return {"skipped": True, "reason": "No golden comments"}

    if not candidates:
        return {
            "skipped": False,
            "true_positives": [],
            "false_positives": [],
            "false_negatives": [
                {"golden_comment": gc["comment"], "severity": gc.get("severity")}
                for gc in golden_comments
            ],
            "errors": [],
            "total_candidates": 0,
            "total_golden": len(golden_comments),
            "tp": 0, "fp": 0, "fn": len(golden_comments),
            "errors_count": 0,
            "precision": 0.0, "recall": 0.0,
        }

    # Score each (golden, candidate) pair
    golden_matched = {
        gc["comment"]: {
            "severity": gc.get("severity"),
            "matched": False,
            "best_confidence": 0.0,
            "matched_candidate": None,
        }
        for gc in golden_comments
    }
    candidate_matched = dict.fromkeys(candidates, False)
    errors = []

    # Process in batches to respect rate limits
    tasks = []
    task_meta = []
    for gc in golden_comments:
        for candidate in candidates:
            tasks.append((gc["comment"], candidate))
            task_meta.append({"golden": gc["comment"], "golden_severity": gc.get("severity"), "candidate": candidate})

    for i in range(0, len(tasks), BATCH_SIZE):
        batch = tasks[i:i + BATCH_SIZE]
        batch_meta = task_meta[i:i + BATCH_SIZE]
        results = await asyncio.gather(
            *[judge.match_comment(g, c) for g, c in batch],
            return_exceptions=True,
        )
        for j, result in enumerate(results):
            meta = batch_meta[j]
            golden = meta["golden"]
            candidate = meta["candidate"]

            if isinstance(result, Exception):
                errors.append({"golden": golden, "candidate": candidate, "error": str(result)})
                continue
            if result.get("error"):
                errors.append({"golden": golden, "candidate": candidate, "error": result["error"]})
                continue
            if result.get("match") and result.get("confidence", 0) > golden_matched[golden]["best_confidence"]:
                golden_matched[golden]["matched"] = True
                golden_matched[golden]["best_confidence"] = result["confidence"]
                golden_matched[golden]["matched_candidate"] = candidate
                golden_matched[golden]["reasoning"] = result.get("reasoning")
                candidate_matched[candidate] = True

        if i + BATCH_SIZE < len(tasks):
            await asyncio.sleep(0.5)

    # Compute metrics
    true_positives = []
    false_negatives = []
    for golden, info in golden_matched.items():
        if info["matched"]:
            true_positives.append({
                "golden_comment": golden,
                "severity": info["severity"],
                "matched_candidate": info["matched_candidate"],
                "confidence": info["best_confidence"],
                "reasoning": info.get("reasoning"),
            })
        else:
            false_negatives.append({"golden_comment": golden, "severity": info["severity"]})

    false_positives = [{"candidate": c} for c, matched in candidate_matched.items() if not matched]
    tp = len(true_positives)
    total_candidates = len(candidates)
    total_golden = len(golden_comments)

    return {
        "skipped": False,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "errors": errors,
        "total_candidates": total_candidates,
        "total_golden": total_golden,
        "tp": tp,
        "fp": len(false_positives),
        "fn": len(false_negatives),
        "errors_count": len(errors),
        "precision": tp / total_candidates if total_candidates > 0 else 0.0,
        "recall": tp / total_golden if total_golden > 0 else 0.0,
    }


def extract_candidates_from_comments(review_comments: list[dict]) -> list[str]:
    """Extract candidate texts from review comments. Simple extraction without LLM."""
    candidates = []
    for c in review_comments:
        body = c.get("body", "").strip()
        if body and len(body) >= 20:
            candidates.append(body)
    return candidates


async def main():
    parser = argparse.ArgumentParser(description="Judge Firebreak results against Martian benchmark")
    parser.add_argument("--tool", default="firebreak", help="Tool to evaluate")
    parser.add_argument("--limit", type=int, help="Limit number of PRs to evaluate")
    parser.add_argument("--force", action="store_true", help="Re-evaluate existing results")
    args = parser.parse_args()

    model = os.environ.get("JUDGE_MODEL", "claude-sonnet-4-5-20250929")

    if not BENCHMARK_DATA.exists():
        print(f"Error: {BENCHMARK_DATA} not found")
        sys.exit(1)

    with open(BENCHMARK_DATA) as f:
        benchmark = json.load(f)

    RESULTS_DIR.mkdir(exist_ok=True)
    eval_file = RESULTS_DIR / f"evaluations_{args.tool}.json"

    # Load existing state
    state = {}
    if eval_file.exists() and not args.force:
        with open(eval_file) as f:
            state = json.load(f)

    judge = AnthropicJudge(model)

    evaluated = 0
    skipped = 0

    for pr_url, entry in benchmark.items():
        if args.limit and evaluated >= args.limit:
            break

        # Find this tool's review
        review = None
        for r in entry.get("reviews", []):
            if r["tool"] == args.tool:
                review = r
                break

        if not review:
            continue

        if pr_url in state and not args.force:
            skipped += 1
            continue

        golden_comments = entry.get("golden_comments", [])
        candidates = extract_candidates_from_comments(review.get("review_comments", []))

        print(f"Evaluating {entry.get('source_repo', '?')}: {entry.get('pr_title', pr_url)[:60]}...")
        print(f"  Golden: {len(golden_comments)}, Candidates: {len(candidates)}")

        result = await evaluate_review(judge, golden_comments, candidates)
        result["tool"] = args.tool
        result["pr_url"] = pr_url

        state[pr_url] = result
        with open(eval_file, "w") as f:
            json.dump(state, f, indent=2)

        p = result["precision"]
        r = result["recall"]
        print(f"  P={p:.1%} R={r:.1%} TP={result['tp']} FP={result['fp']} FN={result['fn']}")
        evaluated += 1

    # Aggregate
    total_tp = sum(r.get("tp", 0) for r in state.values() if not r.get("skipped"))
    total_fp = sum(r.get("fp", 0) for r in state.values() if not r.get("skipped"))
    total_fn = sum(r.get("fn", 0) for r in state.values() if not r.get("skipped"))

    agg_p = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    agg_r = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
    agg_f1 = 2 * agg_p * agg_r / (agg_p + agg_r) if (agg_p + agg_r) > 0 else 0

    print(f"\n{'=' * 60}")
    print(f"Aggregate ({args.tool}): P={agg_p:.1%} R={agg_r:.1%} F1={agg_f1:.1%}")
    print(f"  TP={total_tp} FP={total_fp} FN={total_fn}")
    print(f"  Evaluated: {evaluated}, Skipped: {skipped}")
    print(f"Results: {eval_file}")


if __name__ == "__main__":
    asyncio.run(main())
