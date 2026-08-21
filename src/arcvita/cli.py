from __future__ import annotations

import argparse

from arcvita.pipeline import run_pipeline


def main() -> None:
    ap = argparse.ArgumentParser(description="ArcVita biography pipeline")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("--limit", type=int, default=None, help="limit persons for trial")
    ap.add_argument("--qids", nargs="*", default=None, help="only these QIDs")
    args = ap.parse_args()
    res = run_pipeline(config_path=args.config, limit=args.limit, qids=args.qids)
    print(res)


if __name__ == "__main__":
    main()
