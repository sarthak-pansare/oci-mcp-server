"""Monitoring: alarms + metric queries."""

from __future__ import annotations

import oci

from .client import get_client, tenancy_id
from .util import map_oci_error, s_alarm, strip_nulls


def register(mcp):
    @mcp.tool()
    def list_alarms(compartment_id: str | None = None, limit: int = 50) -> dict:
        """List monitoring alarms."""
        try:
            items = oci.pagination.list_call_get_all_results(
                get_client("monitoring").list_alarms, compartment_id or tenancy_id()
            ).data[:limit]
            return {"items": [s_alarm(a) for a in items]}
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def list_metrics(
        compartment_id: str,
        namespace: str | None = None,
        name: str | None = None,
        limit: int = 50,
    ) -> dict:
        """List metric definitions in a compartment. namespace e.g. oci_computeagent."""
        try:
            details = oci.monitoring.models.ListMetricsDetails(
                namespace=namespace,
                name=name,
            )
            items = get_client("monitoring").list_metrics(compartment_id, details).data[:limit]
            return {
                "items": [
                    strip_nulls(
                        {
                            "name": m.name,
                            "namespace": m.namespace,
                            "dimensions": m.dimensions,
                        }
                    )
                    for m in items
                ]
            }
        except Exception as exc:
            raise map_oci_error(exc) from exc

    @mcp.tool()
    def summarize_metrics(
        compartment_id: str,
        namespace: str,
        query: str,
        start_time: str,
        end_time: str,
        resolution: str = "1m",
    ) -> dict:
        """Run a MQL summary. Times: ISO8601. Query: e.g. 'CpuUtilization[1m].mean()'."""
        try:
            details = oci.monitoring.models.SummarizeMetricsDataDetails(
                namespace=namespace,
                query=query,
                start_time=start_time,
                end_time=end_time,
                resolution=resolution,
            )
            items = get_client("monitoring").summarize_metrics_data(compartment_id, details).data
            return {
                "items": [
                    {
                        "name": m.name,
                        "dimensions": m.dimensions,
                        "points": [{"t": str(p.timestamp), "v": p.value} for p in (m.aggregated_datapoints or [])],
                    }
                    for m in items
                ]
            }
        except Exception as exc:
            raise map_oci_error(exc) from exc
