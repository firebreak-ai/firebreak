#!/usr/bin/env bash
# The lint suite: one check, reported as TAP rows. The rules and the scope are in check.py's header.
exec python3 "$(dirname "$0")/check.py"
