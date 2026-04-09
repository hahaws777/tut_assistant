import argparse
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from intent import classify_intent_hybrid
from state import TeachingState, apply_transition
from storage import fetch_recent_conversation_turns


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def _build_report(
    turns: List[Dict[str, str]],
    intents: List[str],
    unknown_ratio: float,
    jump_hit_rate: float,
    suspicious_cases: List[Dict[str, str]],
    output_path: Path,
) -> None:
    dist = Counter(intents)
    lines: List[str] = []
    lines.append("# Replay Evaluation Report")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- total_turns: {len(turns)}")
    lines.append(f"- unknown_ratio: {unknown_ratio:.4f}")
    lines.append(f"- jump_to_problem_hit_rate: {jump_hit_rate:.4f}")
    lines.append("")
    lines.append("## Intent Distribution")
    for key, value in sorted(dist.items(), key=lambda kv: kv[0]):
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Top Suspicious Cases")
    if not suspicious_cases:
        lines.append("- none")
    else:
        for case in suspicious_cases[:20]:
            lines.append(
                f"- session_id={case['session_id']}, ts={case['ts']}, intent={case['intent']}, text={case['user_text'][:140]}"
            )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay evaluation for conversation turns")
    parser.add_argument("--limit", type=int, default=100, help="Max turns to replay")
    parser.add_argument("--session-id", type=str, default=None, help="Optional session id filter")
    parser.add_argument("--output", type=str, default="eval/replay_report.md", help="Output markdown path")
    parser.add_argument(
        "--enable-llm-fallback",
        action="store_true",
        help="Enable llm fallback in replay intent classification",
    )
    args = parser.parse_args()

    turns = fetch_recent_conversation_turns(limit=args.limit, session_id=args.session_id)
    if not turns:
        print("No replay data found. Need sessions with user messages in local storage.")
        output_path = Path(args.output)
        _build_report([], [], 0.0, 0.0, [], output_path)
        print(f"Replay report written to {output_path}")
        return

    replay_state = TeachingState()
    intents: List[str] = []
    jump_hits = 0
    suspicious_cases: List[Dict[str, str]] = []

    for turn in turns:
        pred_intent, problem_idx, _fallback_used = classify_intent_hybrid(
            turn["user_text"],
            enable_llm_fallback=args.enable_llm_fallback,
        )
        intents.append(pred_intent)
        apply_transition(replay_state, pred_intent, problem_idx)

        if pred_intent == "jump_to_problem":
            jump_hits += 1
        if pred_intent == "unknown" and len(turn["user_text"]) > 30:
            suspicious_cases.append(
                {
                    "session_id": turn["session_id"],
                    "ts": turn["ts"],
                    "intent": pred_intent,
                    "user_text": turn["user_text"],
                }
            )

    unknown_ratio = _safe_div(sum(1 for i in intents if i == "unknown"), len(intents))
    jump_hit_rate = _safe_div(jump_hits, len(turns))
    output_path = Path(args.output)
    _build_report(turns, intents, unknown_ratio, jump_hit_rate, suspicious_cases, output_path)

    print(f"total_turns: {len(turns)}")
    print(f"unknown_ratio: {unknown_ratio:.4f}")
    print(f"jump_to_problem_hit_rate: {jump_hit_rate:.4f}")
    print(f"suspicious_cases: {len(suspicious_cases)}")
    print(f"report_path: {output_path}")


if __name__ == "__main__":
    main()

