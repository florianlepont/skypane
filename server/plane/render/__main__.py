"""`python3 -m server.plane.render` entry point - run from the repo root
so `server.*` resolves. See `cli.py`'s module docstring for the flags.
"""
import sys

from server.plane.render import cli

if __name__ == "__main__":
    sys.exit(cli.main())
