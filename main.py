#!/usr/bin/env python3
"""Entry point for the GitHub Star List Manager CLI."""

from interactive import run

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n\n  Interrupted by user.")
