# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Initial release

### Added
- MCP server exposing 50+ OCI tools across IAM, Compute, Networking, Storage, Database, Load Balancer, OKE (Kubernetes), KMS Vault, Functions, Monitoring, and Resource Search.
- Composite tool `deploy_web_server` provisioning a full VCN+IGW+route+security list+subnet+nginx instance in one call, plus `teardown_stack` for cleanup.
- Token-efficient design: one-line tool docstrings, compact summaries, pagination + limit defaults, null-stripping.
- Universal MCP client support: stdio (default), SSE, and streamable-HTTP transports.
- MCP resources (`oci://config`) and prompts (`deploy_webserver_wizard`, `teardown_compartment`).
- Selectable tool categories via `--enable` / `OCI_MCP_ENABLE` (e.g. `--enable iam,compute,networking`).
- Friendly error mapping for the most common OCI config / auth failures.
- Apache-2.0 license.
- Examples directory, smoke tests, GitHub Actions CI, Dockerfile.

### Known limitations
- Logging, DNS, Events, Streaming, Vault crypto (encrypt/decrypt) deferred to v0.2.
- Auth modes other than `~/.oci/config` API key (instance principal, resource principal) deferred.
