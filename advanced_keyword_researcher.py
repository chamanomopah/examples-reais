"""CLI wrapper — delegates to advanced_keyword_researcher/main.py."""

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "advanced_keyword_researcher"))

from main import cli

if __name__ == "__main__":
    cli()
