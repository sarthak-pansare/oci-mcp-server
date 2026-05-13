"""Database (read-only)."""

from __future__ import annotations

from .client import get_client, tenancy_id
from .util import map_oci_error, page_list, strip_nulls


def register(mcp):
    @mcp.tool()
    def list_db_systems(
        compartment_id: str | None = None, limit: int = 50, page: str | None = None
    ) -> dict:
        """List Oracle Base Database systems."""
        try:
            items, next_page = page_list(
                get_client("database").list_db_systems,
                compartment_id or tenancy_id(),
                limit=limit,
                page=page,
            )
            return strip_nulls(
                {
                    "items": [
                        strip_nulls(
                            {
                                "id": s.id,
                                "name": s.display_name,
                                "state": s.lifecycle_state,
                                "shape": s.shape,
                                "edition": s.database_edition,
                            }
                        )
                        for s in items
                    ],
                    "next_page": next_page,
                }
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_autonomous_databases(
        compartment_id: str | None = None, limit: int = 50, page: str | None = None
    ) -> dict:
        """List Autonomous Databases (ADW/ATP)."""
        try:
            items, next_page = page_list(
                get_client("database").list_autonomous_databases,
                compartment_id or tenancy_id(),
                limit=limit,
                page=page,
            )
            return strip_nulls(
                {
                    "items": [
                        strip_nulls(
                            {
                                "id": a.id,
                                "name": a.display_name,
                                "db_name": a.db_name,
                                "workload": a.db_workload,
                                "state": a.lifecycle_state,
                                "cpus": a.cpu_core_count,
                                "storage_tb": a.data_storage_size_in_tbs,
                            }
                        )
                        for a in items
                    ],
                    "next_page": next_page,
                }
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc
