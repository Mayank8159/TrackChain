# Pydantic schemas for distributed pipeline latency tracing and SRE observability (tc.v1).

from typing import Optional, List, Literal
from pydantic import Field
from src.schemas.common import BaseContractModel


class PipelineTraceModel(BaseContractModel):
    trace_id: str = Field(..., description="Unique UUID trace identifier")
    node_id: str = Field(..., description="Edge node physical identifier (e.g. edge-rpi-01)")
    event_type: Literal["TELEMETRY", "DEFECT", "MEDIA"] = Field(..., description="Event domain type")
    captured_at: int = Field(..., description="Unix epoch timestamp in milliseconds at sensor edge capture")
    ingested_at: int = Field(..., description="Unix epoch timestamp in milliseconds at FastAPI gateway receipt")
    inference_ms: float = Field(..., description="ML / physics inference duration in milliseconds")
    delivered_at: Optional[int] = Field(None, description="Unix epoch timestamp in milliseconds at frontend delivery")
    e2e_ms: Optional[float] = Field(None, description="Total end-to-end latency in milliseconds")
    transport_ms: Optional[float] = Field(None, description="Edge-to-gateway transport latency in milliseconds")
    delivery_ms: Optional[float] = Field(None, description="Gateway-to-client delivery latency in milliseconds")


class NodePerformanceSummaryModel(BaseContractModel):
    node_id: str
    hardware_type: Optional[str] = "Raspberry Pi 5"
    total_events: int
    avg_transport_ms: float
    avg_inference_ms: float
    avg_e2e_ms: float
    p95_e2e_ms: float
    status: Literal["optimal", "warning", "critical"] = "optimal"


class PerformanceMetricsResponse(BaseContractModel):
    window_seconds: int = 300
    total_events: int
    throughput_eps: float
    avg_transport_ms: float
    avg_inference_ms: float
    avg_delivery_ms: float
    avg_e2e_ms: float
    p95_e2e_ms: float
    composite_score: float
    composite_grade: Literal["A", "B", "C", "D", "F"]
    node_summaries: List[NodePerformanceSummaryModel] = Field(default_factory=list)
    recent_traces: List[PipelineTraceModel] = Field(default_factory=list)
