"""Networking: VCN, subnet, IGW, route, security list — plus NAT/Service/DRG gateways."""

from __future__ import annotations

import oci

from .client import get_client, tenancy_id
from .util import map_oci_error, page_list, s_subnet, s_vcn, strip_nulls


def register(mcp):
    @mcp.tool()
    def list_vcns(
        compartment_id: str | None = None, limit: int = 50, page: str | None = None
    ) -> dict:
        """List VCNs."""
        try:
            items, next_page = page_list(
                get_client("network").list_vcns,
                compartment_id or tenancy_id(),
                limit=limit,
                page=page,
            )
            return strip_nulls({"items": [s_vcn(v) for v in items], "next_page": next_page})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def create_vcn(
        compartment_id: str,
        display_name: str,
        cidr_block: str = "10.0.0.0/16",
        dns_label: str | None = None,
    ) -> dict:
        """Create a VCN."""
        try:
            details = oci.core.models.CreateVcnDetails(
                compartment_id=compartment_id,
                display_name=display_name,
                cidr_blocks=[cidr_block],
                dns_label=dns_label,
            )
            return s_vcn(get_client("network").create_vcn(details).data)
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def delete_vcn(vcn_id: str) -> dict:
        """Delete a VCN (must be empty)."""
        try:
            get_client("network").delete_vcn(vcn_id)
            return {"deleted": vcn_id}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_subnets(
        compartment_id: str, vcn_id: str | None = None, limit: int = 50, page: str | None = None
    ) -> dict:
        """List subnets, optionally filtered by VCN."""
        try:
            kwargs = {"vcn_id": vcn_id} if vcn_id else {}
            items, next_page = page_list(
                get_client("network").list_subnets,
                compartment_id,
                limit=limit,
                page=page,
                **kwargs,
            )
            return strip_nulls({"items": [s_subnet(s) for s in items], "next_page": next_page})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def create_subnet(
        compartment_id: str,
        vcn_id: str,
        display_name: str,
        cidr_block: str,
        availability_domain: str | None = None,
        security_list_ids: list[str] | None = None,
        route_table_id: str | None = None,
        dns_label: str | None = None,
        prohibit_public_ip: bool = False,
    ) -> dict:
        """Create a subnet. Omit availability_domain for a regional subnet."""
        try:
            details = oci.core.models.CreateSubnetDetails(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name,
                cidr_block=cidr_block,
                availability_domain=availability_domain,
                security_list_ids=security_list_ids,
                route_table_id=route_table_id,
                dns_label=dns_label,
                prohibit_public_ip_on_vnic=prohibit_public_ip,
            )
            return s_subnet(get_client("network").create_subnet(details).data)
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def create_internet_gateway(
        compartment_id: str, vcn_id: str, display_name: str, is_enabled: bool = True
    ) -> dict:
        """Create an internet gateway."""
        try:
            details = oci.core.models.CreateInternetGatewayDetails(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name,
                is_enabled=is_enabled,
            )
            igw = get_client("network").create_internet_gateway(details).data
            return strip_nulls({"id": igw.id, "name": igw.display_name, "state": igw.lifecycle_state})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def add_default_route(route_table_id: str, gateway_id: str, cidr: str = "0.0.0.0/0") -> dict:
        """Append a route (cidr -> gateway/IGW/NAT/Service GW) to a route table."""
        try:
            net = get_client("network")
            rt = net.get_route_table(route_table_id).data
            rules = list(rt.route_rules or [])
            rules.append(
                oci.core.models.RouteRule(
                    destination=cidr,
                    destination_type="CIDR_BLOCK",
                    network_entity_id=gateway_id,
                )
            )
            net.update_route_table(
                route_table_id, oci.core.models.UpdateRouteTableDetails(route_rules=rules)
            )
            return {"updated": route_table_id, "rules": len(rules)}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def create_security_list(
        compartment_id: str,
        vcn_id: str,
        display_name: str,
        ingress_tcp_ports: list[int] | None = None,
        ingress_cidr: str = "0.0.0.0/0",
    ) -> dict:
        """Create a security list. ingress_tcp_ports defaults to [22, 80, 443]."""
        try:
            ports = ingress_tcp_ports if ingress_tcp_ports is not None else [22, 80, 443]
            ingress = [
                oci.core.models.IngressSecurityRule(
                    protocol="6",
                    source=ingress_cidr,
                    source_type="CIDR_BLOCK",
                    tcp_options=oci.core.models.TcpOptions(
                        destination_port_range=oci.core.models.PortRange(min=p, max=p)
                    ),
                )
                for p in ports
            ]
            egress = [
                oci.core.models.EgressSecurityRule(
                    protocol="all",
                    destination="0.0.0.0/0",
                    destination_type="CIDR_BLOCK",
                )
            ]
            details = oci.core.models.CreateSecurityListDetails(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name,
                ingress_security_rules=ingress,
                egress_security_rules=egress,
            )
            sl = get_client("network").create_security_list(details).data
            return strip_nulls({"id": sl.id, "name": sl.display_name, "state": sl.lifecycle_state})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    # ---- Gateways: NAT, Service, DRG ----

    @mcp.tool()
    def create_nat_gateway(compartment_id: str, vcn_id: str, display_name: str) -> dict:
        """Create a NAT gateway (egress for private subnets)."""
        try:
            details = oci.core.models.CreateNatGatewayDetails(
                compartment_id=compartment_id, vcn_id=vcn_id, display_name=display_name
            )
            ng = get_client("network").create_nat_gateway(details).data
            return strip_nulls(
                {"id": ng.id, "name": ng.display_name, "state": ng.lifecycle_state, "nat_ip": ng.nat_ip}
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_service_gateways(compartment_id: str, vcn_id: str | None = None) -> dict:
        """List service gateways (private access to OCI services)."""
        try:
            kwargs = {"vcn_id": vcn_id} if vcn_id else {}
            items = oci.pagination.list_call_get_all_results(
                get_client("network").list_service_gateways, compartment_id, **kwargs
            ).data
            return {
                "items": [
                    strip_nulls({"id": g.id, "name": g.display_name, "state": g.lifecycle_state, "vcn": g.vcn_id})
                    for g in items
                ]
            }
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def create_service_gateway(
        compartment_id: str, vcn_id: str, display_name: str, service_id: str
    ) -> dict:
        """Create a service gateway. service_id from list_services."""
        try:
            details = oci.core.models.CreateServiceGatewayDetails(
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                display_name=display_name,
                services=[oci.core.models.ServiceIdRequestDetails(service_id=service_id)],
            )
            g = get_client("network").create_service_gateway(details).data
            return strip_nulls({"id": g.id, "name": g.display_name, "state": g.lifecycle_state})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_services() -> dict:
        """List OCI services available via service gateway."""
        try:
            items = get_client("network").list_services().data
            return {"items": [{"id": s.id, "name": s.name, "cidr": s.cidr_block} for s in items]}
        except Exception as exc:
            raise map_oci_error(exc) from exc
