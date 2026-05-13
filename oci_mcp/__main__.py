"""OCI MCP Server entrypoint.

Universal across MCP clients (Claude Code, Claude Desktop, Cursor, Codex, Continue,
VS Code, Zed, Antigravity, etc.). Defaults to stdio; supports HTTP/SSE for remote use.

Token-efficiency notes:
    - One-line tool docstrings
    - Compact summaries for list calls (id+name+state, full via get_*)
    - Pagination (limit, page) on every list tool, default limit 50, cap 200
    - Null fields stripped from responses
    - Verbose mode opt-in
"""

from __future__ import annotations

import argparse
import os
import sys

from mcp.server.fastmcp import FastMCP

from . import (
    composite,
    compute,
    database,
    functions,
    iam,
    loadbalancer,
    monitoring,
    networking,
    oke,
    search,
    storage,
    vault,
)
from .client import region, tenancy_id

ALL_MODULES = {
    "iam": iam,
    "compute": compute,
    "networking": networking,
    "storage": storage,
    "database": database,
    "loadbalancer": loadbalancer,
    "oke": oke,
    "vault": vault,
    "functions": functions,
    "monitoring": monitoring,
    "search": search,
    "composite": composite,
}


def _build_mcp(enabled: list[str]) -> FastMCP:
    mcp = FastMCP("oci")

    for key in enabled:
        ALL_MODULES[key].register(mcp)

    # --- MCP resources (ambient context, cheap) ---
    @mcp.resource("oci://config")
    def _config_resource() -> str:
        """Active OCI tenancy + region."""
        try:
            return f"tenancy={tenancy_id()} region={region()}"
        except Exception as exc:  # noqa: BLE001
            return f"OCI config not loaded: {exc}"

    # --- MCP prompts (workflow starters) ---
    @mcp.prompt()
    def deploy_webserver_wizard(compartment_id: str, name: str = "demo") -> str:
        """Walk the LLM through a full web-server deployment."""
        return (
            f"You are operating on OCI compartment {compartment_id}. "
            f"Deploy a public web server named {name}:\n"
            "1) Call whoami to confirm connection.\n"
            "2) Ask the user for an SSH public key (or read ~/.ssh/id_ed25519.pub if available).\n"
            "3) Call deploy_web_server with the key and a sensible shape (default: VM.Standard.E2.1.Micro).\n"
            "4) After it returns, give the user the public URL and SSH command."
        )

    @mcp.prompt()
    def teardown_compartment(compartment_id: str) -> str:
        """List then offer to terminate all resources in a compartment."""
        return (
            f"Use find_resources to list everything in compartment {compartment_id}. "
            "Summarize by resource type. Ask the user which resources to terminate before doing anything destructive."
        )

    return mcp


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="oci-mcp-server", description="MCP server for Oracle Cloud Infrastructure")
    p.add_argument(
        "--transport",
        default=os.environ.get("OCI_MCP_TRANSPORT", "stdio"),
        choices=["stdio", "sse", "streamable-http"],
        help="MCP transport (default: stdio).",
    )
    p.add_argument("--host", default=os.environ.get("OCI_MCP_HOST", "127.0.0.1"))
    p.add_argument("--port", type=int, default=int(os.environ.get("OCI_MCP_PORT", "3000")))
    p.add_argument(
        "--enable",
        default=os.environ.get("OCI_MCP_ENABLE", "all"),
        help="Comma-separated tool categories or 'all'. "
        f"Categories: {','.join(ALL_MODULES)}",
    )
    args = p.parse_args(argv)

    if args.enable == "all":
        enabled = list(ALL_MODULES.keys())
    else:
        enabled = [k.strip() for k in args.enable.split(",") if k.strip() in ALL_MODULES]
        if not enabled:
            print("No valid categories enabled — falling back to 'all'.", file=sys.stderr)
            enabled = list(ALL_MODULES.keys())

    mcp = _build_mcp(enabled)

    if args.transport == "stdio":
        mcp.run()
    else:
        # FastMCP exposes settings via the underlying class
        mcp.settings.host = args.host
        mcp.settings.port = args.port
        mcp.run(transport=args.transport)
    return 0


if __name__ == "__main__":
    sys.exit(main())
