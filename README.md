# OCI MCP Server

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-orange.svg)](https://modelcontextprotocol.io)

**Drive Oracle Cloud Infrastructure from any MCP-aware LLM client.**

A Model Context Protocol server that exposes the OCI control plane — compute, networking, storage, databases, Kubernetes (OKE), load balancers, KMS vaults, functions, monitoring, and cross-service search — to **any** LLM tool that speaks MCP: Claude Code, Claude Desktop, Cursor, Codex CLI, Continue, VS Code, Zed, Antigravity, and others.

Token-efficient by design: one-line tool descriptions, compact summaries, pagination defaults, null-stripped responses.

---

## What you can do

```text
> Deploy a public web server called demo using my SSH key.
> Show me every resource in compartment XYZ grouped by type.
> Create a flexible Load Balancer fronting subnets A and B.
> List my OKE clusters and their kubernetes versions.
> Summarize CpuUtilization on instance ocid1.instance... for the last hour.
> Tear down the VCN we just created and the instance attached to it.
```

## Tool surface (50+ tools across 12 modules)

| Module        | Highlights |
|---------------|------------|
| `iam`         | whoami, health_check, list_compartments, list_users, list_availability_domains, list_regions |
| `compute`     | list/get/launch/action/terminate instances, list_images, list_shapes, list_instance_vnics |
| `networking`  | VCNs, subnets, internet/NAT/service gateways, route tables, security lists |
| `storage`     | Object Storage buckets, list_objects, block volumes |
| `database`    | DB Systems, Autonomous DB |
| `loadbalancer`| Load Balancer + Network Load Balancer (create/list/delete) |
| `oke`         | OKE clusters, node pools (Container Engine for Kubernetes) |
| `vault`       | KMS vaults + keys (read) |
| `functions`   | Applications + functions (read) |
| `monitoring`  | Alarms, metric definitions, metric summaries (MQL) |
| `search`      | `find_resources` across every OCI resource type |
| `composite`   | `deploy_web_server` (full stack in one shot), `teardown_stack` |

---

## Install

### 1. Prerequisites

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`
- An OCI account ([cloud.oracle.com](https://cloud.oracle.com) — Always-Free tier works)

### 2. Configure OCI credentials

In the OCI Console: avatar → **My profile** → **API keys** → **Add API key** → **Generate API key pair**.

Save the files:

```text
~/.oci/oci_api_key.pem      # private key
~/.oci/config               # config (paste the snippet from the console)
```

Example `~/.oci/config`:

```ini
[DEFAULT]
user=ocid1.user.oc1..xxxx
fingerprint=aa:bb:cc:...
tenancy=ocid1.tenancy.oc1..xxxx
region=us-ashburn-1
key_file=~/.oci/oci_api_key.pem
```

### 3. Clone + install

```bash
git clone https://github.com/sarthak-pansare/oci-mcp-server
cd oci-mcp-server
uv sync
```

---

## Connect to your LLM client

The server is a standard MCP server that speaks **stdio** by default. Most clients only need a small JSON snippet.

### Claude Code (CLI)

```bash
claude mcp add oci -s user -- uv --directory /absolute/path/to/oci-mcp-server run oci-mcp-server
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "oci": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/oci-mcp-server", "run", "oci-mcp-server"]
    }
  }
}
```

### Cursor

Settings → MCP → **+ Add new MCP server**:

```json
{
  "mcpServers": {
    "oci": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/oci-mcp-server", "run", "oci-mcp-server"]
    }
  }
}
```

### Codex CLI

Edit `~/.codex/config.toml`:

```toml
[mcp_servers.oci]
command = "uv"
args = ["--directory", "/absolute/path/to/oci-mcp-server", "run", "oci-mcp-server"]
```

### Continue (VS Code / JetBrains)

In your `.continue/config.yaml`:

```yaml
mcpServers:
  - name: oci
    command: uv
    args: ["--directory", "/absolute/path/to/oci-mcp-server", "run", "oci-mcp-server"]
```

### VS Code (native MCP)

In `.vscode/mcp.json`:

```json
{
  "servers": {
    "oci": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/oci-mcp-server", "run", "oci-mcp-server"]
    }
  }
}
```

### Zed

In `~/.config/zed/settings.json`:

```json
{
  "context_servers": {
    "oci": {
      "command": {
        "path": "uv",
        "args": ["--directory", "/absolute/path/to/oci-mcp-server", "run", "oci-mcp-server"]
      }
    }
  }
}
```

### Antigravity / generic MCP clients

Any client that supports stdio MCP can launch:

```text
command: uv
args:    ["--directory", "/abs/path/to/oci-mcp-server", "run", "oci-mcp-server"]
```

---

## Remote mode (HTTP/SSE)

For shared deployments or web-based clients:

```bash
uv run oci-mcp-server --transport sse --host 0.0.0.0 --port 3000
# or
uv run oci-mcp-server --transport streamable-http --host 0.0.0.0 --port 3000
```

Put it behind an authenticating reverse proxy. See [SECURITY.md](SECURITY.md).

### Docker

```bash
docker build -t oci-mcp-server .
docker run --rm -p 3000:3000 \
  -v ~/.oci:/root/.oci:ro \
  -e OCI_MCP_TRANSPORT=sse \
  oci-mcp-server
```

---

## Configuration

| Env var               | Purpose                                                | Default      |
|-----------------------|--------------------------------------------------------|--------------|
| `OCI_CONFIG_FILE`     | Override OCI config path                               | `~/.oci/config` |
| `OCI_PROFILE`         | Config profile name                                    | `DEFAULT`    |
| `OCI_REGION`          | Override region from config                            | (from file)  |
| `OCI_MCP_TRANSPORT`   | `stdio` \| `sse` \| `streamable-http`                  | `stdio`      |
| `OCI_MCP_HOST`        | Host for HTTP/SSE transports                           | `127.0.0.1`  |
| `OCI_MCP_PORT`        | Port for HTTP/SSE transports                           | `3000`       |
| `OCI_MCP_ENABLE`      | Comma-separated module list, or `all`                  | `all`        |

### Reduce token surface further

If you only need a subset of OCI services, register fewer tools — every tool's description is sent to the LLM on every turn:

```bash
uv run oci-mcp-server --enable iam,compute,networking,composite
```

---

## Token-efficiency strategy

Designed to minimize the cost of using OCI tools with an LLM:

1. **One-line docstrings.** Every tool's description fits on a single line. Across all 50+ tools the schema fits in roughly 2 000 tokens.
2. **Compact summaries by default.** `list_*` calls return `{id, name, state, ...}` — not the full SDK object. Use `verbose=True` or `get_*` for full detail.
3. **Pagination + limits.** Every list call defaults to `limit=50` (max 200) and accepts a `page` token.
4. **Null-stripping.** `None` / empty fields are removed from every response.
5. **Module gating.** `--enable` lets users register only the services they need.

---

## Smoke test

After installing and restarting your client:

```text
1. Run mcp__oci__whoami         → confirms credentials work
2. Run mcp__oci__list_regions   → confirms network path
3. Run mcp__oci__find_resources query: "query all resources"
```

For a full end-to-end deployment:

```text
Deploy a web server called demo with this SSH key: ssh-ed25519 AAAAC3...
```

---

## Roadmap

- v0.2: Logging, DNS, Events, Notifications, Streaming, Vault crypto, full Tagging UX
- v0.3: Instance-principal / resource-principal auth, work-request polling helpers
- v0.4: Terraform-style diffs, cost estimation tool, multi-region fan-out

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). PRs welcome.

## License

Apache-2.0 — see [LICENSE](LICENSE).

## Acknowledgements

- [Anthropic Model Context Protocol](https://modelcontextprotocol.io)
- [Oracle Cloud Infrastructure Python SDK](https://github.com/oracle/oci-python-sdk)
