"""Storage: Object Storage buckets, block volumes."""

from __future__ import annotations

import oci

from .client import get_client, tenancy_id
from .util import map_oci_error, page_list, s_bucket, strip_nulls


def register(mcp):
    @mcp.tool()
    def get_namespace() -> dict:
        """Tenancy's Object Storage namespace string."""
        try:
            return {"namespace": get_client("objectstorage").get_namespace().data}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_buckets(
        compartment_id: str | None = None,
        namespace: str | None = None,
        limit: int = 50,
        page: str | None = None,
    ) -> dict:
        """List buckets."""
        try:
            os_ = get_client("objectstorage")
            ns = namespace or os_.get_namespace().data
            items, next_page = page_list(
                os_.list_buckets, ns, compartment_id or tenancy_id(), limit=limit, page=page
            )
            return strip_nulls(
                {"namespace": ns, "items": [s_bucket(b) for b in items], "next_page": next_page}
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def create_bucket(
        compartment_id: str,
        name: str,
        namespace: str | None = None,
        public_access_type: str = "NoPublicAccess",
    ) -> dict:
        """Create a bucket. public_access_type: NoPublicAccess|ObjectRead|ObjectReadWithoutList."""
        try:
            os_ = get_client("objectstorage")
            ns = namespace or os_.get_namespace().data
            details = oci.object_storage.models.CreateBucketDetails(
                name=name, compartment_id=compartment_id, public_access_type=public_access_type
            )
            b = os_.create_bucket(ns, details).data
            return strip_nulls({"name": b.name, "namespace": ns})
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def delete_bucket(name: str, namespace: str | None = None) -> dict:
        """Delete an empty bucket."""
        try:
            os_ = get_client("objectstorage")
            ns = namespace or os_.get_namespace().data
            os_.delete_bucket(ns, name)
            return {"deleted": name}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_objects(bucket: str, namespace: str | None = None, prefix: str | None = None, limit: int = 100) -> dict:
        """List objects in a bucket."""
        try:
            os_ = get_client("objectstorage")
            ns = namespace or os_.get_namespace().data
            kwargs = strip_nulls({"prefix": prefix})
            r = os_.list_objects(ns, bucket, limit=limit, **kwargs).data
            return strip_nulls(
                {"items": [{"name": o.name, "size": o.size} for o in r.objects], "next": r.next_start_with}
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_volumes(
        compartment_id: str | None = None, limit: int = 50, page: str | None = None
    ) -> dict:
        """List block volumes."""
        try:
            items, next_page = page_list(
                get_client("blockstorage").list_volumes,
                compartment_id or tenancy_id(),
                limit=limit,
                page=page,
            )
            return strip_nulls(
                {
                    "items": [
                        strip_nulls(
                            {
                                "id": v.id,
                                "name": v.display_name,
                                "size_gb": v.size_in_gbs,
                                "state": v.lifecycle_state,
                                "ad": v.availability_domain,
                            }
                        )
                        for v in items
                    ],
                    "next_page": next_page,
                }
            )
        except Exception as exc:
            raise map_oci_error(exc) from exc
