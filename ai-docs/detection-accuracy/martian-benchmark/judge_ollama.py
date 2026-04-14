#!/usr/bin/env python3
"""
LLM judge for Martian benchmark using local Ollama inference.

Drop-in replacement for judge_anthropic.py that uses a local Ollama model
via the OpenAI-compatible API. Free inference, no API key needed.

Usage:
  python3 judge_ollama.py [--tool firebreak] [--model gemma4:31b] [--limit N]
"""

import asyncio
import argparse
import json
import sys
from pathlib import Path

try:
    import httpx
except ImportError:
    # Fall back to urllib for environments without httpx
    httpx = None

BENCHMARK_DATA = Path("/tmp/code-review-benchmark/offline/results/benchmark_data.json")
RESULTS_DIR = Path(__file__).parent / "results"
BATCH_SIZE = 4  # Local inference — keep concurrency modest
TIMEOUT = 120   # Local models can be slower than cloud APIs
OLLAMA_URL = "http://localhost:11434"

JUDGE_PROMPT = """You are evaluating whether two code review comments describe the same underlying problem.

## Golden Comment (the known issue):
{golden_comment}

## Candidate Comment (from the tool being evaluated):
{candidate}

## Matching Rules

Two comments MATCH if they identify the same root cause, even when:
- They use completely different terminology (e.g., "race condition" vs "concurrent access")
- One describes the symptom and the other describes the cause
- One is more specific or detailed than the other
- They point to different lines but describe the same logical flaw
- One says "X is missing" and the other says "without X, Y happens"

Two comments DO NOT MATCH only if they describe genuinely different bugs or concerns.

## Examples of matches:
- "TotalDocs race condition" ↔ "concurrent build race on cache" (same: unsynchronized cache access)
- "error result cached unconditionally" ↔ "missing double-check under write lock" (same: stale/bad data enters cache)
- "methods return not implemented" ↔ "stub DB is dead infrastructure" (same: unimplemented code paths)

## Think step by step:
1. What is the ROOT CAUSE the golden comment identifies?
2. What is the ROOT CAUSE the candidate comment identifies?
3. Are these the same root cause?

Respond with ONLY a JSON object:
{{"reasoning": "1-2 sentence explanation comparing root causes", "match": true/false, "confidence": 0.0-1.0}}"""


class OllamaJudge:
    def __init__(self, model: str, base_url: str = None):
        self.model = model
        self.base_url = base_url or OLLAMA_URL
        self.url = f"{self.base_url}/api/chat"
        print(f"Judge model: {self.model} (Ollama @ {self.base_url})")

        # Verify connectivity
        try:
            import urllib.request
            resp = urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=5)
            models = json.loads(resp.read())
            available = [m["name"] for m in models.get("models", [])]
            if not any(model in name or name.startswith(model) for name in available):
                print(f"WARNING: Model '{model}' not found in Ollama. Available: {available}")
        except Exception as e:
            print(f"WARNING: Could not verify Ollama connectivity: {e}")

    async def match_comment(self, golden_comment: str, candidate: str) -> dict:
        prompt = JUDGE_PROMPT.format(golden_comment=golden_comment, candidate=candidate)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a precise code review evaluator. Always respond with valid JSON."},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.0},
        }

        for attempt in range(3):
            try:
                response_text = await self._post(payload)
                content = response_text.strip()
                # Strip markdown code fences if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                    content = content.strip()
                return json.loads(content)
            except json.JSONDecodeError:
                if attempt == 2:
                    return {"error": "JSON parse failed", "raw": response_text[:200]}
                await asyncio.sleep(1)
            except asyncio.TimeoutError:
                if attempt == 2:
                    return {"error": f"Timed out after {TIMEOUT}s"}
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                if attempt == 2:
                    return {"error": str(e)}
                await asyncio.sleep(2 ** attempt)
        return {"error": "Max retries exceeded"}

    async def _post(self, payload: dict) -> str:
        """POST to Ollama API and return the assistant message content."""
        data = json.dumps(payload).encode()

        # Use httpx if available (better async), fall back to sync urllib in thread
        if httpx:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                resp = await client.post(self.url, content=data, headers={"Content-Type": "application/json"})
                resp.raise_for_status()
                return resp.json()["message"]["content"]
        else:
            import urllib.request
            loop = asyncio.get_event_loop()
            def _sync_post():
                req = urllib.request.Request(self.url, data=data, headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                    return json.loads(resp.read())["message"]["content"]
            return await asyncio.wait_for(loop.run_in_executor(None, _sync_post), timeout=TIMEOUT)


async def evaluate_review(
    judge: OllamaJudge,
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


def summarize_candidate(body: str) -> str:
    """Extract the title and first behavioral description from a finding.

    Long markdown findings confuse smaller judge models. Condense to the
    title line plus the current-behavior and expected-behavior bullets
    (where the actual issue is described), capped at 600 chars.
    """
    lines = body.strip().splitlines()
    parts = []

    # Title: first non-empty line
    for line in lines:
        stripped = line.strip()
        if stripped:
            parts.append(stripped)
            break

    # Extract current/expected behavior lines
    for line in lines:
        lower = line.lower().strip()
        if lower.startswith("- **current behavior"):
            parts.append(line.strip())
        elif lower.startswith("- **expected behavior"):
            parts.append(line.strip())

    summary = "\n".join(parts)
    return summary[:600] if summary else body[:600]


def extract_candidates_from_comments(review_comments: list[dict]) -> list[str]:
    """Extract candidate texts from review comments, condensed for judge."""
    candidates = []
    for c in review_comments:
        body = c.get("body", "").strip()
        if body and len(body) >= 20:
            candidates.append(summarize_candidate(body))
    return candidates


async def main():
    parser = argparse.ArgumentParser(description="Judge Firebreak results using local Ollama model")
    parser.add_argument("--tool", default="firebreak", help="Tool to evaluate")
    parser.add_argument("--model", default="gemma4:e4b", help="Ollama model (default: gemma4:e4b)")
    parser.add_argument("--limit", type=int, help="Limit number of PRs to evaluate")
    parser.add_argument("--force", action="store_true", help="Re-evaluate existing results")
    parser.add_argument("--url", default=OLLAMA_URL, help="Ollama API URL")
    args = parser.parse_args()

    if not BENCHMARK_DATA.exists():
        print(f"Error: {BENCHMARK_DATA} not found")
        print("Run inject_results.py first.")
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

    judge = OllamaJudge(args.model, base_url=args.url)

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
