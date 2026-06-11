#!/usr/bin/env python3
"""Normalize a strategy file for copy-paste into the QuantConnect IDE.

- Strips imports from local-only modules (e.g. ``lean_stubs.*``).
- Ensures ``from AlgorithmImports import *`` is present as the first
  non-``__future__`` import.
- Normalizes line endings to ``\\n`` and trims trailing whitespace.

Reads from a file path, prints the cleaned source to stdout, or with
``--clipboard`` copies to the system clipboard. ``--in-place`` overwrites
the source file.

Usage:

    python tools/format_for_qc.py strategies/my_strategy/main.py --clipboard
    python tools/format_for_qc.py strategies/my_strategy/main.py --in-place
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

LOCAL_IMPORT_RE = re.compile(
    r'^\s*(?:from|import)\s+(?:lean_stubs|lean_engine|AlgorithmFramework\.)[^\n]*\n',
    re.MULTILINE,
)
ALGORITHM_IMPORTS = 'from AlgorithmImports import *\n\n'
FUTURE_BLOCK_RE = re.compile(
    r'^(\s*(?:from __future__ import[^\n]*\n)+)',
    re.MULTILINE,
)


def normalize(src: str) -> str:
    src = LOCAL_IMPORT_RE.sub('', src)
    src = src.replace('\r\n', '\n')

    if 'from AlgorithmImports import' not in src and 'import AlgorithmImports' not in src:
        m = FUTURE_BLOCK_RE.match(src)
        if m:
            insert_at = m.end()
            src = src[:insert_at] + '\n' + ALGORITHM_IMPORTS + src[insert_at:].lstrip('\n')
        else:
            src = ALGORITHM_IMPORTS + src.lstrip()

    lines = [re.sub(r'[ \t]+$', '', line) for line in src.split('\n')]
    return '\n'.join(lines).rstrip() + '\n'


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('path', type=Path, help='Strategy .py file')
    ap.add_argument('--clipboard', action='store_true', help='Copy cleaned source to clipboard')
    ap.add_argument('--in-place', action='store_true', help='Overwrite the file with the cleaned source')
    args = ap.parse_args()

    if not args.path.exists():
        print(f'Not found: {args.path}', file=sys.stderr)
        return 1

    cleaned = normalize(args.path.read_text())

    if args.in_place:
        args.path.write_text(cleaned)
        print(f'Wrote {len(cleaned)} bytes to {args.path}')
    elif args.clipboard:
        import pyperclip
        pyperclip.copy(cleaned)
        print(f'Copied {len(cleaned)} bytes to clipboard.')
    else:
        sys.stdout.write(cleaned)

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
