"""Kept for existing instructions: `streamlit run ui/dashboard.py` runs the console in ui/app.py."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).with_name("app.py")), run_name="__main__")
