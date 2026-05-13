"""Resource Search — query any OCI resource by name/type."""

from __future__ import annotations

import oci

from .client import get_client
from .util import map_oci_error, strip_nulls


def register(mcp):
    @mcp.tool()
    def find_resources(query: str, limit: int = 50) -> dict:
        """Search ALL OCI resources. Examples:
        'query all resources where displayName =~ \"web*\"'
        'query instance resources'
        'query vcn,subnet resources where lifecycleState = \"AVAILABLE\"'
        """
        try:
            details = oci.resource_search.models.StructuredSearchDetails(
                type="Structured", query=query
            )
            items = get_client("resource_search").search_resources(details, limit=limit).data.items
            return {
                "items": [
                    strip_nulls(
                        {
                            "id": r.identifier,
                            "name": r.display_name,
                            "type": r.resource_type,
                            "state": r.lifecycle_state,
                            "compartment": r.compartment_id,
                        }
                    )
                    for r in items
                ]
            }
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_resource_types() -> dict:
        """List all resource types searchable via Resource Search."""
        try:
            items = oci.pagination.list_call_get_all_results(
                get_client("resource_search").list_resource_types
            ).data
            return {"items": [{"name": t.name} for t in items]}
        except Exception as exc:
            raise map_oci_error(exc) from exc
