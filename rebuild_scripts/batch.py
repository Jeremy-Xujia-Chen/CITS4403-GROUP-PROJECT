"""Run a JSON list of ABM cases in worker processes and save a pandas pickle."""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

try:
    from .worker import run
except ImportError:
    from worker import run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--jobs", type=int, default=1)
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error("--jobs must be positive")
    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(cases, list) or not all(isinstance(case, dict) for case in cases):
        parser.error("cases must be a JSON list of objects")
    if args.jobs == 1:
        rows = [run(case) for case in cases]
    else:
        with ProcessPoolExecutor(max_workers=args.jobs) as pool:
            rows = list(pool.map(run, cases))
    import pandas as pd
    args.output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_pickle(args.output)
    print(f"Saved {len(rows)} cases to {args.output}")


if __name__ == "__main__":
    main()
