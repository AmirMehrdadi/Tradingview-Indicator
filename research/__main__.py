import argparse
import json
import sys

from .access import AccessDenied
from .loader import DataError, RetrievalError
from .workflow import run_fetch, analyze_run


def main():
    parser = argparse.ArgumentParser(description="Phase 1: public Development loader and descriptive Stage-0A only")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="Fetch only 2023/2024 plus required warm-up; analyze only valid datasets")
    analyze = sub.add_parser("analyze", help="Recompute from a verified, development-only cache")
    analyze.add_argument("--run-id", required=True)
    args = parser.parse_args()
    try:
        result = run_fetch() if args.command == "fetch" else analyze_run(args.run_id)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
        if args.command == "fetch":
            return 0 if all(status == "DESCRIPTIVE_ONLY" for status in result["years"].values()) else 2
        return 0 if all(x["status"] == "DESCRIPTIVE_ONLY" for x in result.values()) else 2
    except (AccessDenied, DataError, RetrievalError, OSError, ValueError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc), "K_cost_stop": "UNSET"}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
