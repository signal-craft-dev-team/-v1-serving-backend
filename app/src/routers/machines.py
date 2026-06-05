from uuid import UUID
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from ..auth.deps import AuthDep

router = APIRouter()


class OperationalState(str, Enum):
    running = "running"
    stopped = "stopped"
    error = "error"
    unknown = "unknown"


class MachineState(str, Enum):
    unknown = "unknown"
    normal = "normal"
    warning = "warning"
    abnormal = "abnormal"
    critical = "critical"
    offline = "offline"


class PeriodEnum(str, Enum):
    last_24h = "24h"
    last_3d = "3d"
    last_5d = "5d"
    last_7d = "7d"


_PERIOD_INTERVAL = {
    PeriodEnum.last_24h: "24 hours",
    PeriodEnum.last_3d:  "3 days",
    PeriodEnum.last_5d:  "5 days",
    PeriodEnum.last_7d:  "7 days",
}


class MachineStatus(BaseModel):
    machine_id: UUID
    machine_code: str
    label: str | None = None
    operational_state: OperationalState
    operational_score: float | None = None
    current_state: MachineState
    remaining_score: float | None = None
    active_alerts_count: int = 0
    sensor_online: bool
    updated_at: datetime | None = None


class MachinesResponse(BaseModel):
    machines: list[MachineStatus]


class MachineStatusHistoryPoint(BaseModel):
    id: UUID
    operational_state: OperationalState
    operational_score: float | None = None
    current_state: MachineState
    recorded_at: datetime


class MachineDetailResponse(BaseModel):
    machine_id: UUID
    machine_code: str
    label: str | None = None
    place_id: UUID
    operational_state: OperationalState
    operational_score: float | None = None
    current_state: MachineState
    remaining_score: float | None = None
    active_alerts_count: int = 0
    sensor_online: bool
    status_updated_at: datetime | None = None
    machine_status_history: list[MachineStatusHistoryPoint]


# ─────────────────────────────────────────
# GET /machines
# ─────────────────────────────────────────
@router.get("/machines", response_model=MachinesResponse, summary="머신 현재 상태 목록", tags=["머신"])
async def get_machines(request: Request, ctx: AuthDep):
    conn = request.app.state.pool

    rows = await conn.fetch(
        """
        SELECT
            m.id            AS machine_id,
            m.machine_code,
            m.label,
            COALESCE(ms.operational_state, 'unknown')   AS operational_state,
            ms.operational_score,
            COALESCE(ms.current_state, 'unknown')       AS current_state,
            ms.remaining_score,
            COALESCE(ms.active_alerts_count, 0)         AS active_alerts_count,
            ms.updated_at,
            EXISTS (
                SELECT 1 FROM sensor_heartbeats sh
                JOIN edge_sensor es ON sh.sensor_id = es.id
                WHERE es.machine_id = m.id
                  AND sh.recorded_at > NOW() - INTERVAL '10 minutes'
            ) AS sensor_online
        FROM machine m
        LEFT JOIN machine_status ms ON ms.machine_id = m.id
        WHERE m.customer_id = $1
          AND m.is_active = true
        ORDER BY m.machine_code
        """,
        ctx.customer_id,
    )

    return MachinesResponse(machines=[dict(row) for row in rows])


# ─────────────────────────────────────────
# GET /machines/{machine_id}
# ─────────────────────────────────────────
@router.get("/machines/{machine_id}", response_model=MachineDetailResponse, summary="머신 상세 + 상태 이력", tags=["머신"])
async def get_machine_detail(machine_id: UUID, period: PeriodEnum, request: Request, ctx: AuthDep):
    conn = request.app.state.pool

    machine_row = await conn.fetchrow(
        """
        SELECT
            m.id            AS machine_id,
            m.machine_code,
            m.label,
            m.place_id,
            COALESCE(ms.operational_state, 'unknown')   AS operational_state,
            ms.operational_score,
            COALESCE(ms.current_state, 'unknown')       AS current_state,
            ms.remaining_score,
            COALESCE(ms.active_alerts_count, 0)         AS active_alerts_count,
            ms.updated_at                               AS status_updated_at,
            EXISTS (
                SELECT 1 FROM sensor_heartbeats sh
                JOIN edge_sensor es ON sh.sensor_id = es.id
                WHERE es.machine_id = m.id
                  AND sh.recorded_at > NOW() - INTERVAL '10 minutes'
            ) AS sensor_online
        FROM machine m
        LEFT JOIN machine_status ms ON ms.machine_id = m.id
        WHERE m.id = $1
          AND m.customer_id = $2
        """,
        machine_id, ctx.customer_id,
    )

    if not machine_row:
        raise HTTPException(status_code=404, detail="해당 머신을 찾을 수 없습니다.")

    interval = _PERIOD_INTERVAL[period]
    history_rows = await conn.fetch(
        f"""
        SELECT id, operational_state, operational_score, current_state, recorded_at
        FROM machine_status_history
        WHERE machine_id = $1
          AND recorded_at > NOW() - INTERVAL '{interval}'
        ORDER BY recorded_at DESC
        LIMIT $2
        """,
        machine_id, request.app.state.settings.MAX_SERIES_POINTS
        if hasattr(request.app.state, "settings") else 5000,
    )

    return MachineDetailResponse(
        **dict(machine_row),
        machine_status_history=[dict(r) for r in history_rows],
    )
