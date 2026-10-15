"""Re-execute the notebooks in place (reads the committed dataset and existing results only).

Needs the development requirements: pip install -r requirements-dev.txt
Run: python -m shahid.run_notebooks   (executes notebooks/*.ipynb, prints the time each takes)
"""
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient


def main():
    for p in sorted(Path("notebooks").glob("*.ipynb")):
        nb = nbformat.read(p, as_version=4)
        t = time.time()
        NotebookClient(nb, timeout=600, kernel_name="python3",
                       resources={"metadata": {"path": str(p.parent)}}).execute()
        nbformat.write(nb, p)
        print(f"{p}: executed in {time.time() - t:.0f} s", flush=True)


if __name__ == "__main__":
    main()
