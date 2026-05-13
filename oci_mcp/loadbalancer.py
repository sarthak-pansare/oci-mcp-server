"""Load Balancer + Network Load Balancer."""

from __future__ import annotations

import oci

from .client import get_client, tenancy_id
from .util import map_oci_error, page_list, s_lb, strip_nulls


def register(mcp):
    @mcp.tool()
    def list_load_balancers(
        compartment_id: str | None = None, limit: int = 50, page: str | None = None
    ) -> dict:
        """List public/private Load Balancers."""
        try:
            items, next_page = page_list(
                get_client("lb").list_load_balancers,
                compartment_id or tenancy_id(),
                limit=limit,
                page=page,
            )
            return strip_nulls({"items": [s_lb(lb) for lb in items], "next_page": next_page})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def create_load_balancer(
        compartment_id: str,
        display_name: str,
        subnet_ids: list[str],
        shape: str = "flexible",
        is_private: bool = False,
        min_bandwidth_mbps: int = 10,
        max_bandwidth_mbps: int = 100,
    ) -> dict:
        """Create a flexible Load Balancer. subnet_ids: one regional or two ADs."""
        try:
            details = oci.load_balancer.models.CreateLoadBalancerDetails(
                compartment_id=compartment_id,
                display_name=display_name,
                shape_name=shape,
                is_private=is_private,
                subnet_ids=subnet_ids,
                shape_details=oci.load_balancer.models.ShapeDetails(
                    minimum_bandwidth_in_mbps=min_bandwidth_mbps,
                    maximum_bandwidth_in_mbps=max_bandwidth_mbps,
                )
                if shape == "flexible"
                else None,
            )
            work = get_client("lb").create_load_balancer(details)
            return {"work_request_id": work.headers.get("opc-work-request-id")}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def delete_load_balancer(load_balancer_id: str) -> dict:
        """Delete a Load Balancer."""
        try:
            get_client("lb").delete_load_balancer(load_balancer_id)
            return {"deleted": load_balancer_id}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_network_load_balancers(
        compartment_id: str | None = None, limit: int = 50, page: str | None = None
    ) -> dict:
        """List Network Load Balancers (L4)."""
        try:
            data, next_page = page_list(
                get_client("nlb").list_network_load_balancers,
                compartment_id or tenancy_id(),
                limit=limit,
                page=page,
            )
            # NLB returns a NetworkLoadBalancerCollection wrapper; LB returns a plain list.
            raw_items = data.items if hasattr(data, "items") else data
            return strip_nulls(
                {
                    "items": [
                        strip_nulls(
                            {
                                "id": n.id,
                                "name": n.display_name,
                                "state": n.lifecycle_state,
                                "ips": [ip.ip_address for ip in (n.ip_addresses or [])],
                            }
                        )
                        for n in raw_items
                    ],
                    "next_page": next_page,
                }
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc
