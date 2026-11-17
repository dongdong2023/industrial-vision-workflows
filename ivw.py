#!/usr/bin/env python3
import sys
from ivw.cli import main

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

if __name__ == "__main__":
    raise SystemExit(main())
