"""High-level one-shot orchestrations."""

from __future__ import annotations

import time

import oci

from .client import get_client
from .util import b64, map_oci_error, s_instance, s_vcn, strip_nulls

CLOUD_INIT_NGINX = """#!/bin/bash
set -eux
dnf install -y nginx
systemctl enable --now nginx
firewall-cmd --permanent --add-service=http || true
firewall-cmd --permanent --add-service=https || true
firewall-cmd --reload || true
cat >/usr/share/nginx/html/index.html <<HTML
<!doctype html><html><head><title>OCI MCP</title></head>
<body style="font-family:system-ui;max-width:640px;margin:60px auto;line-height:1.5">
<h1>Hello from $(hostname)</h1><p>Deployed via OCI MCP server.</p>
</body></html>
HTML
"""


def _wait(get_fn, rid, states, timeout=900, poll=5):
    start = time.time()
    while time.time() - start < timeout:
        r = get_fn(rid).data
        if r.lifecycle_state in states:
            return r
        time.sleep(poll)
    raise TimeoutError(f"{rid} not in {states} after {timeout}s")


def register(mcp):
    @mcp.tool()
    def deploy_web_server(
        compartment_id: str,
        name: str,
        ssh_public_key: str,
        shape: str = "VM.Standard.E2.1.Micro",
        operating_system: str = "Oracle Linux",
        operating_system_version: str = "8",
        vcn_cidr: str = "10.0.0.0/16",
        subnet_cidr: str = "10.0.1.0/24",
        shape_ocpus: float | None = None,
        shape_memory_in_gbs: float | None = None,
    ) -> dict:
        """One-shot: VCN+IGW+route+seclist+subnet+nginx instance. Returns public_ip + URL."""
        try:
            ident = get_client("identity")
            net = get_client("network")
            compute = get_client("compute")

            ads = ident.list_availability_domains(compartment_id).data
            if not ads:
                raise RuntimeError("No availability domains")
            ad = ads[0].name

            images = oci.pagination.list_call_get_all_results(
                compute.list_images,
                compartment_id,
                operating_system=operating_system,
                operating_system_version=operating_system_version,
                shape=shape,
                sort_by="TIMECREATED",
                sort_order="DESC",
            ).data
            if not images:
                raise RuntimeError(f"No image for {operating_system} {operating_system_version} {shape}")
            image_id = images[0].id

            vcn = net.create_vcn(
                oci.core.models.CreateVcnDetails(
                    compartment_id=compartment_id,
                    display_name=f"{name}-vcn",
                    cidr_blocks=[vcn_cidr],
                    dns_label=name.replace("-", "")[:15].lower() or "mcpvcn",
                )
            ).data
            vcn = _wait(net.get_vcn, vcn.id, {"AVAILABLE"})

            igw = net.create_internet_gateway(
                oci.core.models.CreateInternetGatewayDetails(
                    compartment_id=compartment_id,
                    vcn_id=vcn.id,
                    display_name=f"{name}-igw",
                    is_enabled=True,
                )
            ).data
            igw = _wait(net.get_internet_gateway, igw.id, {"AVAILABLE"})

            rt = net.get_route_table(vcn.default_route_table_id).data
            rules = list(rt.route_rules or [])
            rules.append(
                oci.core.models.RouteRule(
                    destination="0.0.0.0/0",
                    destination_type="CIDR_BLOCK",
                    network_entity_id=igw.id,
                )
            )
            net.update_route_table(rt.id, oci.core.models.UpdateRouteTableDetails(route_rules=rules))

            sl = net.create_security_list(
                oci.core.models.CreateSecurityListDetails(
                    compartment_id=compartment_id,
                    vcn_id=vcn.id,
                    display_name=f"{name}-seclist",
                    ingress_security_rules=[
                        oci.core.models.IngressSecurityRule(
                            protocol="6",
                            source="0.0.0.0/0",
                            source_type="CIDR_BLOCK",
                            tcp_options=oci.core.models.TcpOptions(
                                destination_port_range=oci.core.models.PortRange(min=p, max=p)
                            ),
                        )
                        for p in (22, 80, 443)
                    ],
                    egress_security_rules=[
                        oci.core.models.EgressSecurityRule(
                            protocol="all",
                            destination="0.0.0.0/0",
                            destination_type="CIDR_BLOCK",
                        )
                    ],
                )
            ).data
            sl = _wait(net.get_security_list, sl.id, {"AVAILABLE"})

            subnet = net.create_subnet(
                oci.core.models.CreateSubnetDetails(
                    compartment_id=compartment_id,
                    vcn_id=vcn.id,
                    display_name=f"{name}-subnet",
                    cidr_block=subnet_cidr,
                    security_list_ids=[sl.id],
                    route_table_id=vcn.default_route_table_id,
                    dns_label="public",
                )
            ).data
            subnet = _wait(net.get_subnet, subnet.id, {"AVAILABLE"})

            shape_cfg = None
            if shape_ocpus is not None or shape_memory_in_gbs is not None:
                shape_cfg = oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=shape_ocpus or 1, memory_in_gbs=shape_memory_in_gbs or 6
                )

            inst = compute.launch_instance(
                oci.core.models.LaunchInstanceDetails(
                    availability_domain=ad,
                    compartment_id=compartment_id,
                    display_name=name,
                    shape=shape,
                    shape_config=shape_cfg,
                    source_details=oci.core.models.InstanceSourceViaImageDetails(
                        source_type="image", image_id=image_id
                    ),
                    metadata={"ssh_authorized_keys": ssh_public_key, "user_data": b64(CLOUD_INIT_NGINX)},
                    create_vnic_details=oci.core.models.CreateVnicDetails(
                        subnet_id=subnet.id, assign_public_ip=True
                    ),
                )
            ).data
            inst = _wait(compute.get_instance, inst.id, {"RUNNING"})

            atts = oci.pagination.list_call_get_all_results(
                compute.list_vnic_attachments, compartment_id, instance_id=inst.id
            ).data
            public_ip = private_ip = None
            for att in atts:
                v = net.get_vnic(att.vnic_id).data
                if v.is_primary:
                    public_ip, private_ip = v.public_ip, v.private_ip
                    break

            return strip_nulls(
                {
                    "status": "deployed",
                    "instance": s_instance(inst),
                    "vcn": s_vcn(vcn),
                    "subnet_id": subnet.id,
                    "igw_id": igw.id,
                    "seclist_id": sl.id,
                    "public_ip": public_ip,
                    "private_ip": private_ip,
                    "url": f"http://{public_ip}/" if public_ip else None,
                    "ssh": f"ssh opc@{public_ip}" if public_ip else None,
                    "note": "Allow ~30-60s after RUNNING for cloud-init to finish.",
                }
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def teardown_stack(
        compartment_id: str,
        instance_id: str | None = None,
        vcn_id: str | None = None,
    ) -> dict:
        """Terminate an instance and tear down its VCN (subnets, gateways, security lists).

        Order: instance(s) -> subnets -> clear route tables -> IGW/NAT/Service gateways
        -> non-default security lists -> non-default route tables -> VCN.
        """
        try:
            net = get_client("network")
            compute = get_client("compute")
            killed: list[dict] = []
            problems: list[dict] = []

            if instance_id:
                compute.terminate_instance(instance_id, preserve_boot_volume=False)
                killed.append({"instance": instance_id})
                _wait(compute.get_instance, instance_id, {"TERMINATED"})

            if not vcn_id:
                return {"removed": killed}

            # 1) Subnets
            for s in oci.pagination.list_call_get_all_results(
                net.list_subnets, compartment_id, vcn_id=vcn_id
            ).data:
                try:
                    net.delete_subnet(s.id)
                    killed.append({"subnet": s.id})
                except Exception as e:
                    problems.append({"subnet": s.id, "error": str(e)})

            # 2) Clear route rules on every route table in the VCN (removes
            #    references to gateways so they can be deleted next).
            for rt in oci.pagination.list_call_get_all_results(
                net.list_route_tables, compartment_id, vcn_id=vcn_id
            ).data:
                try:
                    net.update_route_table(
                        rt.id, oci.core.models.UpdateRouteTableDetails(route_rules=[])
                    )
                except Exception as e:
                    problems.append({"route_table_clear": rt.id, "error": str(e)})

            # 3) Gateways (IGW, NAT, Service)
            for g in oci.pagination.list_call_get_all_results(
                net.list_internet_gateways, compartment_id, vcn_id=vcn_id
            ).data:
                try:
                    net.delete_internet_gateway(g.id)
                    killed.append({"igw": g.id})
                except Exception as e:
                    problems.append({"igw": g.id, "error": str(e)})
            for g in oci.pagination.list_call_get_all_results(
                net.list_nat_gateways, compartment_id, vcn_id=vcn_id
            ).data:
                try:
                    net.delete_nat_gateway(g.id)
                    killed.append({"nat_gw": g.id})
                except Exception as e:
                    problems.append({"nat_gw": g.id, "error": str(e)})
            for g in oci.pagination.list_call_get_all_results(
                net.list_service_gateways, compartment_id, vcn_id=vcn_id
            ).data:
                try:
                    net.delete_service_gateway(g.id)
                    killed.append({"service_gw": g.id})
                except Exception as e:
                    problems.append({"service_gw": g.id, "error": str(e)})

            # 4) Non-default security lists
            for sl in oci.pagination.list_call_get_all_results(
                net.list_security_lists, compartment_id, vcn_id=vcn_id
            ).data:
                if sl.display_name.startswith("Default"):
                    continue
                try:
                    net.delete_security_list(sl.id)
                    killed.append({"seclist": sl.id})
                except Exception as e:
                    problems.append({"seclist": sl.id, "error": str(e)})

            # 5) Non-default route tables (default RT goes with the VCN)
            for rt in oci.pagination.list_call_get_all_results(
                net.list_route_tables, compartment_id, vcn_id=vcn_id
            ).data:
                if rt.display_name.startswith("Default"):
                    continue
                try:
                    net.delete_route_table(rt.id)
                    killed.append({"route_table": rt.id})
                except Exception as e:
                    problems.append({"route_table": rt.id, "error": str(e)})

            # 6) VCN
            try:
                net.delete_vcn(vcn_id)
                killed.append({"vcn": vcn_id})
            except Exception as e:
                problems.append({"vcn": vcn_id, "error": str(e)})

            out: dict = {"removed": killed}
            if problems:
                out["problems"] = problems
            return out
        except Exception as exc:
            raise map_oci_error(exc) from exc
