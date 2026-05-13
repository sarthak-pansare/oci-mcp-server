"""Smoke tests — no OCI credentials required.

These verify the server wires up correctly: every module imports, every tool
registers, and the entrypoint argparse works.
"""

from __future__ import annotations

from oci_mcp import (
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
from oci_mcp.__main__ import ALL_MODULES, _build_mcp
from oci_mcp.util import (
    OCIError,
    clamp_limit,
    map_oci_error,
    s_compartment,
    strip_nulls,
)

ALL_MODS = [iam, compute, networking, storage, database, loadbalancer, oke, vault, functions, monitoring, search, composite]


def test_modules_have_register():
    for m in ALL_MODS:
        assert hasattr(m, "register"), f"{m.__name__} missing register()"


def test_all_modules_registered_in_main():
    assert set(ALL_MODULES.keys()) == {
        "iam",
        "compute",
        "networking",
        "storage",
        "database",
        "loadbalancer",
        "oke",
        "vault",
        "functions",
        "monitoring",
        "search",
        "composite",
    }


def test_build_mcp_registers_all_tools():
    mcp = _build_mcp(list(ALL_MODULES.keys()))
    names = {t.name for t in mcp._tool_manager._tools.values()}
    # Spot-check key tools across categories
    must_have = {
        "whoami",
        "health_check",
        "list_compartments",
        "list_instances",
        "launch_instance",
        "list_vcns",
        "create_vcn",
        "create_nat_gateway",
        "create_service_gateway",
        "list_buckets",
        "list_db_systems",
        "list_load_balancers",
        "list_clusters",
        "list_vaults",
        "list_applications",
        "list_alarms",
        "find_resources",
        "deploy_web_server",
        "teardown_stack",
    }
    missing = must_have - names
    assert not missing, f"missing tools: {missing}"
    assert len(names) >= 40, f"expected 40+ tools, got {len(names)}"


def test_subset_enable():
    mcp = _build_mcp(["iam", "compute"])
    names = {t.name for t in mcp._tool_manager._tools.values()}
    assert "whoami" in names
    assert "list_instances" in names
    assert "create_vcn" not in names  # not enabled


def test_clamp_limit():
    assert clamp_limit(None) == 50
    assert clamp_limit(0) == 1
    assert clamp_limit(1000) == 200
    assert clamp_limit(10) == 10


def test_strip_nulls():
    assert strip_nulls({"a": 1, "b": None, "c": "", "d": [], "e": "x"}) == {"a": 1, "e": "x"}


def test_oci_error_mapping_unknown():
    err = map_oci_error(ValueError("nope"))
    assert isinstance(err, OCIError)
    assert "nope" in str(err)


def test_s_compartment_handles_minimum_fields():
    class Fake:
        id = "ocid1.compartment..1"
        name = "demo"
        lifecycle_state = "ACTIVE"

    assert s_compartment(Fake()) == {"id": "ocid1.compartment..1", "name": "demo", "state": "ACTIVE"}


def test_entrypoint_argparse_subset():
    # Importing main shouldn't trigger network or auth
    from oci_mcp.__main__ import main  # noqa: F401
