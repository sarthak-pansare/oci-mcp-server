"""IAM tools."""

from __future__ import annotations

from .client import get_client, region, tenancy_id, user_id
from .util import map_oci_error, page_list, s_compartment, strip_nulls


def register(mcp):
    @mcp.tool()
    def whoami() -> dict:
        """Tenancy/user/region from loaded OCI config — canonical 'connected?' check."""
        try:
            ident = get_client("identity")
            t = ident.get_tenancy(tenancy_id()).data
            u = ident.get_user(user_id()).data
            return strip_nulls(
                {
                    "tenancy": t.name,
                    "tenancy_id": t.id,
                    "user": u.name,
                    "user_id": u.id,
                    "region": region(),
                    "home_region_key": t.home_region_key,
                    "connected": True,
                }
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def health_check() -> dict:
        """Ping OCI: list regions, return count."""
        try:
            n = len(get_client("identity").list_regions().data)
            return {"ok": True, "regions": n, "current": region()}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_compartments(
        parent: str | None = None,
        limit: int = 50,
        page: str | None = None,
        subtree: bool = True,
    ) -> dict:
        """List compartments under a parent (default: tenancy)."""
        try:
            ident = get_client("identity")
            items, next_page = page_list(
                ident.list_compartments,
                parent or tenancy_id(),
                limit=limit,
                page=page,
                compartment_id_in_subtree=subtree,
                access_level="ACCESSIBLE",
            )
            return strip_nulls(
                {"items": [s_compartment(c) for c in items], "next_page": next_page}
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_users(limit: int = 50, page: str | None = None) -> dict:
        """List IAM users."""
        try:
            ident = get_client("identity")
            items, next_page = page_list(ident.list_users, tenancy_id(), limit=limit, page=page)
            return strip_nulls(
                {
                    "items": [
                        strip_nulls({"id": u.id, "name": u.name, "email": u.email, "state": u.lifecycle_state})
                        for u in items
                    ],
                    "next_page": next_page,
                }
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_availability_domains(compartment_id: str | None = None) -> dict:
        """List availability domains (default compartment: tenancy)."""
        try:
            ads = get_client("identity").list_availability_domains(compartment_id or tenancy_id()).data
            return {"items": [ad.name for ad in ads]}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_regions() -> dict:
        """List all OCI regions."""
        try:
            return {"items": [{"key": r.key, "name": r.name} for r in get_client("identity").list_regions().data]}
        except Exception as exc:
            raise map_oci_error(exc) from exc
