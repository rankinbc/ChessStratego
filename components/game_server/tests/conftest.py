"""Make the `app` package importable no matter where pytest is invoked from."""

import sys
from pathlib import Path

COMPONENT_DIR = Path(__file__).resolve().parent.parent
if str(COMPONENT_DIR) not in sys.path:
    sys.path.insert(0, str(COMPONENT_DIR))
