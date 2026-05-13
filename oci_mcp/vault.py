"""KMS — Vaults + Keys (read)."""

from __future__ import annotations

import oci

from .client import get_client, tenancy_id
from .util import map_oci_error, s_vault, strip_nulls


def register(mcp):
    @mcp.tool()
    def list_vaults(compartment_id: str | None = None, limit: int = 50) -> dict:
        """List KMS vaults."""
        try:
            items = oci.pagination.list_call_get_all_results(
                get_client("vault").list_vaults, compartment_id or tenancy_id()
            ).data[:limit]
            return {"items": [s_vault(v) for v in items]}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def get_vault(vault_id: str) -> dict:
        """Get a vault."""
        try:
            v = get_client("vault").get_vault(vault_id).data
            return strip_nulls(
                {
                    "id": v.id,
                    "name": v.display_name,
                    "type": v.vault_type,
                    "state": v.lifecycle_state,
                    "management_endpoint": v.management_endpoint,
                    "crypto_endpoint": v.crypto_endpoint,
                }
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_keys(compartment_id: str, management_endpoint: str, limit: int = 50) -> dict:
        """List keys in a vault. Get management_endpoint from get_vault."""
        try:
            cfg = oci.config.from_file()
            kms = oci.key_management.KmsManagementClient(cfg, management_endpoint)
            items = oci.pagination.list_call_get_all_results(
                kms.list_keys, compartment_id
            ).data[:limit]
            return {
                "items": [
                    strip_nulls(
                        {
                            "id": k.id,
                            "name": k.display_name,
                            "state": k.lifecycle_state,
                            "algorithm": getattr(k, "algorithm", None),
                        }
                    )
                    for k in items
                ]
            }
        except Exception as exc:
            raise map_oci_error(exc) from exc
