"""Compute tools: instances, images, shapes."""

from __future__ import annotations

import oci

from .client import get_client, tenancy_id
from .util import map_oci_error, page_list, s_image, s_instance, strip_nulls, to_dict


def register(mcp):
    @mcp.tool()
    def list_instances(
        compartment_id: str | None = None,
        limit: int = 50,
        page: str | None = None,
    ) -> dict:
        """List compute instances."""
        try:
            items, next_page = page_list(
                get_client("compute").list_instances,
                compartment_id or tenancy_id(),
                limit=limit,
                page=page,
            )
            return strip_nulls({"items": [s_instance(i) for i in items], "next_page": next_page})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def get_instance(instance_id: str, verbose: bool = False) -> dict:
        """Get one instance. verbose=true returns full SDK object."""
        try:
            i = get_client("compute").get_instance(instance_id).data
            return to_dict(i) if verbose else s_instance(i)
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_images(
        compartment_id: str | None = None,
        operating_system: str | None = None,
        operating_system_version: str | None = None,
        shape: str | None = None,
        limit: int = 25,
        page: str | None = None,
    ) -> dict:
        """List platform images, newest first."""
        try:
            kwargs = strip_nulls(
                {
                    "operating_system": operating_system,
                    "operating_system_version": operating_system_version,
                    "shape": shape,
                }
            )
            items, next_page = page_list(
                get_client("compute").list_images,
                compartment_id or tenancy_id(),
                limit=limit,
                page=page,
                sort_by="TIMECREATED",
                sort_order="DESC",
                **kwargs,
            )
            return strip_nulls({"items": [s_image(i) for i in items], "next_page": next_page})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_shapes(
        compartment_id: str | None = None,
        availability_domain: str | None = None,
        limit: int = 50,
    ) -> dict:
        """List compute shapes available in a compartment."""
        try:
            kwargs = {"availability_domain": availability_domain} if availability_domain else {}
            items = oci.pagination.list_call_get_all_results(
                get_client("compute").list_shapes,
                compartment_id or tenancy_id(),
                **kwargs,
            ).data[:limit]
            return {
                "items": [
                    strip_nulls(
                        {
                            "shape": s.shape,
                            "ocpus": getattr(s, "ocpus", None),
                            "memory_gb": getattr(s, "memory_in_gbs", None),
                        }
                    )
                    for s in items
                ]
            }
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def launch_instance(
        compartment_id: str,
        display_name: str,
        shape: str,
        subnet_id: str,
        image_id: str,
        ssh_public_key: str,
        availability_domain: str | None = None,
        user_data_b64: str | None = None,
        assign_public_ip: bool = True,
        shape_ocpus: float | None = None,
        shape_memory_in_gbs: float | None = None,
    ) -> dict:
        """Launch a compute instance. Use shape_ocpus/memory for flex shapes."""
        try:
            compute = get_client("compute")
            if availability_domain is None:
                availability_domain = (
                    get_client("identity").list_availability_domains(compartment_id).data[0].name
                )
            metadata = {"ssh_authorized_keys": ssh_public_key}
            if user_data_b64:
                metadata["user_data"] = user_data_b64
            shape_cfg = None
            if shape_ocpus is not None or shape_memory_in_gbs is not None:
                shape_cfg = oci.core.models.LaunchInstanceShapeConfigDetails(
                    ocpus=shape_ocpus or 1, memory_in_gbs=shape_memory_in_gbs or 6
                )
            details = oci.core.models.LaunchInstanceDetails(
                availability_domain=availability_domain,
                compartment_id=compartment_id,
                display_name=display_name,
                shape=shape,
                shape_config=shape_cfg,
                source_details=oci.core.models.InstanceSourceViaImageDetails(
                    source_type="image", image_id=image_id
                ),
                metadata=metadata,
                create_vnic_details=oci.core.models.CreateVnicDetails(
                    subnet_id=subnet_id, assign_public_ip=assign_public_ip
                ),
            )
            return s_instance(compute.launch_instance(details).data)
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def instance_action(instance_id: str, action: str) -> dict:
        """Power action. action: START|STOP|SOFTSTOP|RESET|SOFTRESET."""
        action = action.upper()
        if action not in {"START", "STOP", "SOFTSTOP", "RESET", "SOFTRESET"}:
            return {"error": f"invalid action '{action}'"}
        try:
            return s_instance(get_client("compute").instance_action(instance_id, action).data)
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def terminate_instance(instance_id: str, preserve_boot_volume: bool = False) -> dict:
        """Terminate an instance."""
        try:
            get_client("compute").terminate_instance(
                instance_id, preserve_boot_volume=preserve_boot_volume
            )
            return {"terminated": instance_id, "preserve_boot_volume": preserve_boot_volume}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_instance_vnics(compartment_id: str, instance_id: str) -> dict:
        """List VNIC attachments (incl. public IP) for an instance."""
        try:
            compute = get_client("compute")
            net = get_client("network")
            atts = oci.pagination.list_call_get_all_results(
                compute.list_vnic_attachments, compartment_id, instance_id=instance_id
            ).data
            out = []
            for att in atts:
                v = net.get_vnic(att.vnic_id).data
                out.append(
                    strip_nulls(
                        {
                            "id": v.id,
                            "private_ip": v.private_ip,
                            "public_ip": v.public_ip,
                            "subnet": v.subnet_id,
                            "primary": v.is_primary,
                        }
                    )
                )
            return {"items": out}
        except Exception as exc:
            raise map_oci_error(exc) from exc
