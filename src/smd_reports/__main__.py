"""Allow the same commands through python -m smd_reports."""

from .cli import main

raise SystemExit(main())
