#!/usr/bin/env python3
"""Parse a QuantConnect traceback and surface local file:line references.

Reads from stdin by default, or from --file/--clipboard. Filters frames to
only those under the repo root, prints a ``path:line (function)`` list, and
optionally opens them in VS Code with ``code -g``.

Usage:

    # paste from clipboard
    python tools/parse_error.py --clipboard --open

    # pipe a saved traceback
    python tools/parse_error.py < /tmp/qc_error.txt

    # from a file
    python tools/parse_error.py --file /tmp/qc_error.txt
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FRAME_RE = re.compile(r'File "([^"]+)", line (\d+)(?:, in (.+?))?(?=\n|$)')


def parse_frames(text: str) -> list[tuple[str, int, str | None]]:
    return [(p, int(n), func) for p, n, func in FRAME_RE.findall(text)]


def filter_local(
    frames: list[tuple[str, int, str | None]],
) -> list[tuple[Path, int, str | None]]:
    out: list[tuple[Path, int, str | None]] = []
    root = ROOT.resolve()
    for raw, line, func in frames:
        p = Path(raw)
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        try:
            rel = p.resolve().relative_to(root)
        except ValueError:
            continue
        out.append((rel, line, func))
    return out


def read_input(args: argparse.Namespace) -> str:
    if args.clipboard:
        import pyperclip
        return pyperclip.paste()
    if args.file:
        return args.file.read_text()
    return sys.stdin.read()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--clipboard', action='store_true', help='Read from system clipboard')
    ap.add_argument('--file', type=Path, help='Read from file')
    ap.add_argument('--open', action='store_true', help='Open matched locations in VS Code')
    ap.add_argument('--limit', type=int, default=20, help='Max frames to show (default 20)')
    args = ap.parse_args()

    text = read_input(args)
    if not text.strip():
        print('No input text received.', file=sys.stderr)
        return 1

    frames = filter_local(parse_frames(text))
    if not frames:
        print('No local frames found in traceback.')
        return 0

    print(f'Local frames ({len(frames)}):')
    for rel, line, func in frames[: args.limit]:
        label = func or '<module>'
        print(f'  {rel}:{line}  ({label})')
    if len(frames) > args.limit:
        print(f'  ... ({len(frames) - args.limit} more, raise --limit to see all)')

    if args.open:
        for rel, line, _ in frames:
            subprocess.run(['code', '-g', f'{rel}:{line}'], cwd=ROOT, check=False)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
