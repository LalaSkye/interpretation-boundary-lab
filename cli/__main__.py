"""Allow running as python -m cli."""

from cli.main import main
import sys

sys.exit(main())
