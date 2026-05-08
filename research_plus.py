"""CLI wrapper — delegates to research_plus/main.py."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "research_plus"))

from main import cli

if __name__ == "__main__":
    cli()
