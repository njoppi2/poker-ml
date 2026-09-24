"""Compatibility entry point for the reproducible training CLI.

Prefer: python -m game_engine.training.benchmark --help
"""
if __package__ in (None, ""):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from game_engine.training.benchmark import main

if __name__ == "__main__":
    main()
