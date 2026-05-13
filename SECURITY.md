# Security policy

## Supported versions

The latest minor release is supported. Older releases receive security fixes on a best-effort basis.

## Reporting a vulnerability

**Do not open a public issue for security problems.**

Please report vulnerabilities by emailing the maintainer or opening a private GitHub Security Advisory:

- GitHub: https://github.com/sarthak-pansare/oci-mcp-server/security/advisories/new

We'll acknowledge within 72 hours and aim to ship a fix within 14 days for high-severity issues.

## Scope

This MCP server holds OCI API credentials with the privileges granted to the configured IAM user. Be aware that:

- **Tools that create or destroy resources are powerful.** Anyone with access to this MCP server (any LLM/client connected to it) can launch compute instances, delete VCNs, terminate databases, etc. — and Oracle charges money for those resources.
- **Credentials**: never commit `~/.oci/config` or `*.pem` private keys. They are excluded by `.gitignore`.
- **Principle of least privilege**: create a dedicated IAM user/group with only the policies you need (e.g. allow group oci-mcp-users to manage instance-family in compartment dev).
- **Public deployment**: if running with `--transport sse` exposed to the internet, place it behind an authenticating reverse proxy. The MCP server has no built-in auth.

## Hardening tips

- Use compartments to scope blast radius. Run the MCP server against a `sandbox` compartment by default.
- Rotate the API key periodically (delete + regenerate via OCI Console).
- Audit usage via OCI Audit Service.
