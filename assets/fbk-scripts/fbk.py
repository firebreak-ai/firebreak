"""fbk.py — single entry point dispatcher for all context asset invocations."""

import importlib
import os
import sys

script_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(1, script_dir)

if sys.version_info < (3, 11):
    print(f"Error: Python 3.11+ required (found {sys.version})", file=sys.stderr)
    sys.exit(2)

from fbk import COMMAND_MAP

if len(sys.argv) < 2 or sys.argv[1] not in COMMAND_MAP:
    command = sys.argv[1] if len(sys.argv) > 1 else None
    if command:
        print(f"Error: unrecognized command '{command}'", file=sys.stderr)
    else:
        print("Error: no command given", file=sys.stderr)
    print("Available commands:", file=sys.stderr)
    for name in sorted(COMMAND_MAP):
        print(f"  {name}", file=sys.stderr)
    sys.exit(2)

command_name = sys.argv[1]
remaining_args = sys.argv[2:]
module_path = COMMAND_MAP[command_name]

module = importlib.import_module(module_path)
sys.argv = [command_name] + remaining_args
result = module.main()
sys.exit(result if result is not None else 0)
