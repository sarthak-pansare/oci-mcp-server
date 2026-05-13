"""Shared helpers — kept tight to minimize LLM token cost on every call."""

from __future__ import annotations

import base64
from collections.abc import Iterable
from typing import Any

import oci

DEFAULT_LIMIT = 50
MAX_LIMIT = 200


class OCIError(Exception):
    """Friendly error with an actionable next step."""


def b64(text: str) -> str:
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(int(limit), MAX_LIMIT))


def pick(obj: Any, fields: Iterable[str]) -> dict:
    """Pull a small set of fields off an SDK model, dropping nulls."""
    out: dict[str, Any] = {}
    for f in fields:
        v = getattr(obj, f, None)
        if v is None or v == "":
            continue
        out[f] = str(v) if hasattr(v, "isoformat") else v
    return out


def strip_nulls(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in (None, "", [], {})}


def to_dict(obj: Any) -> dict:
    """Convert an OCI SDK model into a JSON-serializable dict (stripping nulls)."""
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return {k: to_dict(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [to_dict(v) for v in obj]
    if hasattr(obj, "attribute_map"):
        out: dict = {}
        for attr in obj.attribute_map:
            val = getattr(obj, attr, None)
            if val is None or val == "":
                continue
            if isinstance(val, (list, dict)) or hasattr(val, "attribute_map"):
                converted = to_dict(val)
                if converted in ({}, []):
                    continue
                out[attr] = converted
            elif isinstance(val, (str, int, float, bool)):
                out[attr] = val
            else:
                out[attr] = str(val)
        return out
    return str(obj)


# ---- Compact per-resource summarizers (small, stable token footprint) ----

def s_instance(i) -> dict:
    return strip_nulls(
        {
            "id": i.id,
            "name": i.display_name,
            "state": i.lifecycle_state,
            "shape": i.shape,
            "ad": i.availability_domain,
            "region": getattr(i, "region", None),
        }
    )


def s_vcn(v) -> dict:
    return strip_nulls(
        {
            "id": v.id,
            "name": v.display_name,
            "cidr": (v.cidr_blocks or [v.cidr_block])[0] if (v.cidr_blocks or v.cidr_block) else None,
            "state": v.lifecycle_state,
            "default_rt": v.default_route_table_id,
            "default_sl": v.default_security_list_id,
        }
    )


def s_subnet(s) -> dict:
    return strip_nulls(
        {
            "id": s.id,
            "name": s.display_name,
            "cidr": s.cidr_block,
            "vcn": s.vcn_id,
            "ad": s.availability_domain,
            "state": s.lifecycle_state,
        }
    )


def s_bucket(b) -> dict:
    return strip_nulls({"name": b.name, "compartment": b.compartment_id})


def s_image(i) -> dict:
    return strip_nulls(
        {
            "id": i.id,
            "name": i.display_name,
            "os": i.operating_system,
            "os_version": i.operating_system_version,
            "state": i.lifecycle_state,
        }
    )


def s_compartment(c) -> dict:
    return strip_nulls(
        {"id": c.id, "name": c.name, "state": c.lifecycle_state}
    )


def s_lb(lb) -> dict:
    return strip_nulls(
        {
            "id": lb.id,
            "name": lb.display_name,
            "state": lb.lifecycle_state,
            "shape": getattr(lb, "shape_name", None),
            "ips": [ip.ip_address for ip in (lb.ip_addresses or [])] if hasattr(lb, "ip_addresses") else None,
        }
    )


def s_cluster(c) -> dict:
    return strip_nulls(
        {
            "id": c.id,
            "name": c.name,
            "state": c.lifecycle_state,
            "k8s_version": c.kubernetes_version,
            "vcn": c.vcn_id,
        }
    )


def s_vault(v) -> dict:
    return strip_nulls(
        {"id": v.id, "name": v.display_name, "type": v.vault_type, "state": v.lifecycle_state}
    )


def s_app(a) -> dict:
    return strip_nulls(
        {"id": a.id, "name": a.display_name, "state": a.lifecycle_state}
    )


def s_alarm(a) -> dict:
    return strip_nulls(
        {"id": a.id, "name": a.display_name, "state": a.lifecycle_state, "severity": a.severity}
    )


# ---- Error mapping ----

def map_oci_error(exc: BaseException) -> OCIError:
    if isinstance(exc, oci.exceptions.ServiceError):
        return OCIError(
            f"OCI {exc.status} {exc.code}: {exc.message} (op={exc.operation_name})"
        )
    if isinstance(exc, oci.exceptions.ConfigFileNotFound):
        return OCIError(
            "OCI config missing. Create ~/.oci/config with tenancy/user/fingerprint/key_file/region. "
            "See README."
        )
    if isinstance(exc, oci.exceptions.InvalidConfig):
        return OCIError(f"OCI config invalid: {exc}. Fix the offending field in ~/.oci/config.")
    if isinstance(exc, oci.exceptions.InvalidPrivateKey):
        return OCIError("OCI private key invalid. Regenerate the API key and replace the .pem.")
    return OCIError(f"{type(exc).__name__}: {exc}")


# ---- Pagination wrapper ----

def page_list(api_call, *args, limit: int | None = None, page: str | None = None, **kwargs):
    """Call a list API with limit + page; return (items, next_page)."""
    n = clamp_limit(limit)
    resp = api_call(*args, limit=n, page=page, **kwargs) if page else api_call(*args, limit=n, **kwargs)
    return resp.data, resp.headers.get("opc-next-page")
