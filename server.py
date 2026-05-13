"""Thin shim for the existing `uv run server.py` entrypoint.

The canonical entrypoint is `python -m oci_mcp` (or the `oci-mcp-server` script
installed by `pip install`). This shim is kept so existing client registrations
that point at server.py keep working.
"""

from oci_mcp.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
