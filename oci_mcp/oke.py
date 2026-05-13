"""OKE — Oracle Container Engine for Kubernetes."""

from __future__ import annotations

import oci

from .client import get_client, tenancy_id
from .util import map_oci_error, s_cluster, strip_nulls


def register(mcp):
    @mcp.tool()
    def list_clusters(compartment_id: str | None = None, limit: int = 50) -> dict:
        """List OKE clusters."""
        try:
            items = oci.pagination.list_call_get_all_results(
                get_client("oke").list_clusters, compartment_id or tenancy_id()
            ).data[:limit]
            return {"items": [s_cluster(c) for c in items]}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def get_cluster(cluster_id: str) -> dict:
        """Get OKE cluster."""
        try:
            return s_cluster(get_client("oke").get_cluster(cluster_id).data)
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def create_cluster(
        compartment_id: str,
        name: str,
        vcn_id: str,
        kubernetes_version: str,
        service_subnet_id: str | None = None,
        pod_subnet_id: str | None = None,
    ) -> dict:
        """Create an OKE cluster (basic; node pool added separately)."""
        try:
            details = oci.container_engine.models.CreateClusterDetails(
                name=name,
                compartment_id=compartment_id,
                vcn_id=vcn_id,
                kubernetes_version=kubernetes_version,
                options=oci.container_engine.models.ClusterCreateOptions(
                    service_lb_subnet_ids=[service_subnet_id] if service_subnet_id else None,
                ),
            )
            wr = get_client("oke").create_cluster(details)
            return {"work_request_id": wr.headers.get("opc-work-request-id")}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def delete_cluster(cluster_id: str) -> dict:
        """Delete an OKE cluster."""
        try:
            wr = get_client("oke").delete_cluster(cluster_id)
            return {"work_request_id": wr.headers.get("opc-work-request-id")}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_node_pools(compartment_id: str, cluster_id: str | None = None, limit: int = 50) -> dict:
        """List OKE node pools."""
        try:
            kwargs = {"cluster_id": cluster_id} if cluster_id else {}
            items = oci.pagination.list_call_get_all_results(
                get_client("oke").list_node_pools, compartment_id, **kwargs
            ).data[:limit]
            return {
                "items": [
                    strip_nulls(
                        {
                            "id": n.id,
                            "name": n.name,
                            "cluster": n.cluster_id,
                            "k8s_version": n.kubernetes_version,
                            "shape": getattr(n, "node_shape", None),
                        }
                    )
                    for n in items
                ]
            }
        except Exception as exc:
            raise map_oci_error(exc) from exc
