# Pydantic schemas for dashboard summary cards and live SCADA status (tc.v1).

from typing import Dict
from src.schemas.common import BaseContractModel


class DashboardSummaryResponse(BaseContractModel):
    total_defects: int
    critical_defects: int
    distance_covered_km: float
    avg_speed_kmh: float
    open_alerts: int
    defect_counts_by_class: Dict[str, int]
    severity_distribution: Dict[str, int]
