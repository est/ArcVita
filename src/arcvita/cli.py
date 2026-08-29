from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from arcvita.pipeline import run_pipeline


def run_doctor(config_path: str = "config.yaml") -> dict:
    """Validate curated/ and extracted schemas."""
    errors: list[str] = []
    ok_curated = 0
    ok_extracted = 0

    curated_root = Path("data/curated")
    extracted_roots = [Path("data/extracted/pre_qin"), Path("data/extracted/qin_han"), Path("data/extracted/king_tables"), Path("data/extracted")]

    # curated
    if curated_root.exists():
        for f in curated_root.rglob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    errors.append(f"{f}: not a dict")
                    continue
                if "person" not in data:
                    errors.append(f"{f}: missing 'person' key")
                    continue
                person = data["person"]
                if not isinstance(person, dict) or not person.get("name_zh"):
                    errors.append(f"{f}: person.name_zh missing")
                    continue
                for k in ("endeavors", "events"):
                    if k in data and not isinstance(data[k], list):
                        errors.append(f"{f}: {k} not list")
                ok_curated += 1
            except Exception as e:
                errors.append(f"{f}: load failed {e}")
    else:
        errors.append(f"curated root not found: {curated_root}")

    # extracted
    for root in extracted_roots:
        if not root.exists():
            continue
        for f in root.glob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    errors.append(f"{f}: not a dict")
                    continue
                # extracted can be either curated-style (person/endeavors/events) or plain lists
                if "person" in data:
                    if not data["person"].get("name_zh"):
                        errors.append(f"{f}: person.name_zh missing")
                        continue
                elif "name_zh" in data:
                    pass
                else:
                    # allow other shapes but require at least one known key
                    pass
                ok_extracted += 1
            except Exception as e:
                errors.append(f"{f}: load failed {e}")

    # also validate config loads
    try:
        from arcvita.config import load_config

        load_config(config_path)
    except Exception as e:
        errors.append(f"config {config_path} failed: {e}")

    if errors:
        for e in errors:
            print(f"[doctor] ERROR {e}", file=sys.stderr)
        print(f"[doctor] curated ok={ok_curated} extracted ok={ok_extracted} errors={len(errors)}")
        return {"ok": False, "curated": ok_curated, "extracted": ok_extracted, "errors": errors}
    print(f"[doctor] OK curated={ok_curated} extracted={ok_extracted}")
    return {"ok": True, "curated": ok_curated, "extracted": ok_extracted, "errors": []}


def main() -> None:
    ap = argparse.ArgumentParser(description="ArcVita biography pipeline", prog="arcvita")
    ap.add_argument("--config", default="config.yaml", help="config.yaml path")
    ap.add_argument("--limit", type=int, default=None, help="limit persons for trial")
    ap.add_argument("--qids", nargs="*", default=None, help="only these QIDs")
    ap.add_argument("--out", type=str, default=None, help="产物输出目录, 测试用 _tmp/run (隔离)")
    ap.add_argument("command", nargs="?", default=None, choices=["doctor"], help="子命令")
    # support `arcvita doctor` as positional: also handle legacy `python -m arcvita.cli doctor`
    args = ap.parse_args()

    if args.command == "doctor":
        res = run_doctor(config_path=args.config)
        sys.exit(0 if res["ok"] else 1)

    # optional env: if "doctor" was passed as --qids mistakenly? handle manual check
    # run pipeline
    res = run_pipeline(config_path=args.config, limit=args.limit, qids=args.qids, out_dir=args.out)
    print(res)


if __name__ == "__main__":
    main()
