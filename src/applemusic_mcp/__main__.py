"""Entry point for running as a module: python -m applemusic_mcp"""

import sys

if __name__ == "__main__":
    # Preserve bare `python -m applemusic_mcp` as a stdio server, while allowing
    # the documented CLI verbs (including bridge) when arguments are supplied.
    if len(sys.argv) > 1:
        from .cli import main
    else:
        from .server import main

    main()
