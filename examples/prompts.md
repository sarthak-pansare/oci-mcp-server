# Prompt recipes

Copy-paste these into your LLM client once the OCI MCP server is connected.

## 1. Verify connection

> Run `mcp__oci__whoami` and tell me my tenancy, user, and region.

## 2. Inventory a compartment

> Use `mcp__oci__find_resources` with the query `query all resources where compartmentId = '<OCID>'`. Group the results by resource type and give me counts.

## 3. Deploy a public web server (full stack)

> Deploy a public web server called `demo`:
> 1. Read `~/.ssh/id_ed25519.pub` (ask me if it doesn't exist).
> 2. Call `mcp__oci__deploy_web_server` with that SSH key, my dev compartment, shape `VM.Standard.E2.1.Micro`.
> 3. After it returns, give me the URL and `ssh` command.

## 4. Right-size an instance

> List my instances, then for the busiest one (most CPU) run `mcp__oci__summarize_metrics` with namespace `oci_computeagent` and query `CpuUtilization[1m].mean()` for the last 24 hours. Recommend a shape based on average + p95.

## 5. Kubernetes overview

> List my OKE clusters and, for each, list its node pools with shape and node count.

## 6. Tear down (careful!)

> List instances and VCNs in compartment `<OCID>`. For each VCN created in the last 7 days, ask me before calling `mcp__oci__teardown_stack`.

## 7. Network design audit

> List every VCN. For each: count subnets, list whether it has an Internet Gateway, NAT Gateway, and Service Gateway. Flag VCNs missing egress.

## 8. Object Storage cost scan

> List my buckets. For each, sample `list_objects` (limit 500) and sum the `size` field. Sort by size descending. Note: this is a sample, not a precise total.

## 9. Database inventory

> List both `list_db_systems` and `list_autonomous_databases` across my compartments. Build a single table sorted by lifecycle state.

## 10. Multi-region fan-out

> For each region returned by `list_regions`, switch `OCI_REGION` via env (or use a separate MCP profile) and run `list_instances`. Build a global inventory.
