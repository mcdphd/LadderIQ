"""Compatibility entry point for LadderIQ generation.

The strategy and presentation logic now live in generate_ladder.py and
investment_engine.py. Keeping this wrapper preserves the existing publish
workflow without allowing an older embedded generator to overwrite v3.60.
"""
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parent
runpy.run_path(str(ROOT / "generate_ladder.py"), run_name="__main__")
