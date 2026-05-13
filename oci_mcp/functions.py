"""OCI Functions (serverless)."""

from __future__ import annotations

import oci

from .client import get_client, tenancy_id
from .util import map_oci_error, s_app, strip_nulls


def register(mcp):
    @mcp.tool()
    def list_applications(compartment_id: str | None = None, limit: int = 50) -> dict:
        """List Functions applications."""
        try:
            items = oci.pagination.list_call_get_all_results(
                get_client("functions").list_applications, compartment_id or tenancy_id()
            ).data[:limit]
            return {"items": [s_app(a) for a in items]}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_functions(application_id: str, limit: int = 50) -> dict:
        """List functions in an application."""
        try:
            items = oci.pagination.list_call_get_all_results(
                get_client("functions").list_functions, application_id
            ).data[:limit]
            return {
                "items": [
                    strip_nulls(
                        {
                            "id": f.id,
                            "name": f.display_name,
                            "state": f.lifecycle_state,
                            "image": f.image,
                            "memory_mb": f.memory_in_mbs,
                            "timeout_s": f.timeout_in_seconds,
                            "invoke_endpoint": f.invoke_endpoint,
                        }
                    )
                    for f in items
                ]
            }
        except Exception as exc:
            raise map_oci_error(exc) from exc
