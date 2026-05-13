# Contributing

Thanks for taking the time to contribute.

## Quick start

```bash
git clone https://github.com/your-username/oci-mcp-server
cd oci-mcp-server
uv sync --extra dev
uv run pytest
uv run ruff check .
```

## Project layout

```
oci_mcp/
  __main__.py        CLI entrypoint + transport selection
  client.py          OCI client cache (auth + factories)
  util.py            Summarizers + pagination + error mapping
  iam.py             Compartments, users, regions, ADs
  compute.py         Instances, images, shapes
  networking.py      VCN, subnet, IGW, NAT, Service GW, security lists, routes
  storage.py         Object Storage, block volumes
  database.py        DB Systems, Autonomous DB
  loadbalancer.py    LB + NLB
  oke.py             Kubernetes (Container Engine)
  vault.py           KMS vaults + keys
  functions.py       OCI Functions
  monitoring.py      Alarms + metric queries
  search.py          Resource Search (cross-service)
  composite.py       High-level one-shot orchestrations
```

## Adding a tool

1. Add it to the relevant module (or create a new module).
2. Register it via the module's `register(mcp)` function.
3. **Keep the docstring to one line.** Every char of docstring is sent to the LLM on every turn — keep it tight.
4. **Default list calls to `limit=50` and accept a `page` token.** Stream output only when needed.
5. **Return compact dicts.** Prefer `s_instance(i)` over `to_dict(i)` for list responses. Use `verbose=True` opt-in for full SDK objects.
6. Strip nulls (`strip_nulls`) — fewer bytes, less noise.

## Adding a new service

1. Add a factory entry to `oci_mcp/client.py` under `_FACTORIES`.
2. Create `oci_mcp/<service>.py` with a `register(mcp)` function.
3. Register the module in `oci_mcp/__main__.py` `ALL_MODULES`.

## Testing

Smoke tests don't require OCI credentials — they verify imports and tool registration. Run with:

```bash
uv run pytest
```

For integration tests against a live OCI tenancy, set `OCI_MCP_LIVE=1` and ensure `~/.oci/config` is valid.

## Style

- Ruff handles formatting and linting (`uv run ruff check . && uv run ruff format .`).
- Prefer plain dicts over Pydantic models for return types (lower token cost).
- No unnecessary abstraction — three similar lines are better than a premature helper.

## Release process

1. Bump version in `pyproject.toml`.
2. Update `CHANGELOG.md`.
3. Tag: `git tag v0.X.Y && git push --tags`.
4. CI publishes to PyPI on tag push (once secret is configured).
