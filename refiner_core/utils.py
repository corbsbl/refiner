from pathlib import Path
import sys


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)
