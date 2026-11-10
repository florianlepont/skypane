"""Command line for the skin-tone trial: ``python -m server.photo``."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from server.photo import trial
from server.photo.normalize import PhotoRejected


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m server.photo",
        description="Render dithered previews of a photo, or the synthetic skin-tone grid.",
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--in", dest="infile", help="photo to preview (keep it outside the repository)")
    src.add_argument("--synthetic", action="store_true", help="render the synthetic skin-tone grid")
    p.add_argument("--out", help="output directory outside the repository")
    p.add_argument("--fit", default="fill", help="fill or bands")
    p.add_argument("--pos-x", type=float, default=0.5)
    p.add_argument("--pos-y", type=float, default=0.5)
    return p


def _run_synthetic(out: str | None) -> int:
    out_dir = trial.check_out_dir(out) if out else trial.check_out_dir(trial.default_out_dir())
    rows = trial.run_grid(out_dir)
    print(trial.format_rows(rows))
    for sheet in sorted(out_dir.glob("skin-tone-*.png")):
        print(sheet)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.synthetic:
            return _run_synthetic(args.out)
        if not args.out:
            print("error: --out is required with --in", file=sys.stderr)
            return 2
        for path in trial.render_file(args.infile, args.out, args.fit, args.pos_x, args.pos_y):
            print(path)
        return 0
    except PhotoRejected as exc:
        print(f"rejected: {exc.reason}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
