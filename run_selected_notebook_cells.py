from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("notebook", type=Path)
    parser.add_argument("cells", nargs="+", type=int)
    args = parser.parse_args()

    os.environ.setdefault("MPLBACKEND", "Agg")

    nb_path = args.notebook
    nb = json.loads(nb_path.read_text(encoding="utf-8", errors="ignore"))
    ns = {"__name__": "__main__", "__file__": str(nb_path)}

    for cell_no in args.cells:
        print(f"===== Ejecutando cell {cell_no} =====", flush=True)
        try:
            src = "".join(nb["cells"][cell_no - 1].get("source", []))
            exec(compile(src, f"{nb_path.name}:cell{cell_no}", "exec"), ns)
        except Exception:
            print(f"===== ERROR cell {cell_no} =====", flush=True)
            traceback.print_exc()
            return 1
        print(f"===== OK cell {cell_no} =====", flush=True)

    print("===== DONE =====", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
