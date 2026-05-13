"""OCI client factory.

Loads ~/.oci/config (overridable via env vars), validates it on first use, and
hands out lazily-constructed, cached service clients.
"""

from __future__ import annotations

import os
import threading
from collections.abc import Callable

import oci

from .util import OCIError, map_oci_error

_lock = threading.Lock()
_cfg: dict | None = None
_clients: dict[str, object] = {}


def _config() -> dict:
    global _cfg
    if _cfg is not None:
        return _cfg
    with _lock:
        if _cfg is not None:
            return _cfg
        path = os.environ.get("OCI_CONFIG_FILE", oci.config.DEFAULT_LOCATION)
        profile = os.environ.get("OCI_PROFILE", oci.config.DEFAULT_PROFILE)
        try:
            cfg = oci.config.from_file(file_location=path, profile_name=profile)
            if region := os.environ.get("OCI_REGION"):
                cfg["region"] = region
            oci.config.validate_config(cfg)
        except Exception as exc:  # noqa: BLE001
            raise map_oci_error(exc) from exc
        _cfg = cfg
        return cfg


def config() -> dict:
    """Return the loaded OCI config dict (with env-var overrides applied)."""
    return _config()


def tenancy_id() -> str:
    return _config()["tenancy"]


def user_id() -> str:
    return _config()["user"]


def region() -> str:
    return _config()["region"]


_FACTORIES: dict[str, Callable[[dict], object]] = {
    "identity": oci.identity.IdentityClient,
    "compute": oci.core.ComputeClient,
    "compute_mgmt": oci.core.ComputeManagementClient,
    "network": oci.core.VirtualNetworkClient,
    "blockstorage": oci.core.BlockstorageClient,
    "objectstorage": oci.object_storage.ObjectStorageClient,
    "database": oci.database.DatabaseClient,
    "lb": oci.load_balancer.LoadBalancerClient,
    "nlb": oci.network_load_balancer.NetworkLoadBalancerClient,
    "oke": oci.container_engine.ContainerEngineClient,
    "vault": oci.key_management.KmsVaultClient,
    "functions": oci.functions.FunctionsManagementClient,
    "monitoring": oci.monitoring.MonitoringClient,
    "resource_search": oci.resource_search.ResourceSearchClient,
}


def get_client(name: str):
    """Return a cached OCI service client by short name."""
    if name not in _FACTORIES:
        raise OCIError(f"Unknown OCI client '{name}'. Known: {sorted(_FACTORIES)}")
    if name in _clients:
        return _clients[name]
    with _lock:
        if name not in _clients:
            try:
                _clients[name] = _FACTORIES[name](_config())
            except Exception as exc:  # noqa: BLE001
                raise map_oci_error(exc) from exc
        return _clients[name]


def reset_cache() -> None:
    """Drop cached config/clients (used after credential changes)."""
    global _cfg
    with _lock:
        _cfg = None
        _clients.clear()
