from uuid import UUID
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from enum import Enum
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from ..auth.deps import AuthDep

KST = timezone(timedelta(hours=9))


def _to_kst(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(KST)

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


_PERIOD_DELTA = {
    PeriodEnum.last_24h: timedelta(hours=24),
    PeriodEnum.last_3d:  timedelta(days=3),
    PeriodEnum.last_5d:  timedelta(days=5),
    PeriodEnum.last_7d:  timedelta(days=7),
}

_PERIOD_BUCKET_MINUTES = {
    PeriodEnum.last_24h: 5,
    PeriodEnum.last_3d:  15,
    PeriodEnum.last_5d:  30,
    PeriodEnum.last_7d:  30,
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


class StatusSegment(BaseModel):
    bucket_start: datetime
    state: str  # "running" | "stopped" | "no_data"
    avg_score: float | None = None


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
    status_segments: list[StatusSegment]


def _build_segments(
    rows: list,
    period_start: datetime,
    bucket_minutes: int,
    now: datetime,
) -> list[StatusSegment]:
    bucket_map: dict[int, list[float]] = defaultdict(list)
    for row in rows:
        recorded_at = row["recorded_at"]
        if recorded_at.tzinfo is None:
            recorded_at = recorded_at.replace(tzinfo=timezone.utc)
        offset_minutes = (recorded_at - period_start).total_seconds() / 60
        bucket_idx = int(offset_minutes // bucket_minutes)
        if row["operational_score"] is not None:
            bucket_map[bucket_idx].append(float(row["operational_score"]))

    total_buckets = int((now - period_start).total_seconds() / 60 // bucket_minutes) + 1

    segments = []
    for i in range(total_buckets):
        bucket_start = period_start + timedelta(minutes=i * bucket_minutes)
        scores = bucket_map.get(i, [])
        if not scores:
            state = "no_data"
            avg_score = None
        else:
            avg_score = sum(scores) / len(scores)
            state = "running" if avg_score >= 0.5 else "stopped"
        segments.append(StatusSegment(
            bucket_start=_to_kst(bucket_start),
            state=state,
            avg_score=round(avg_score, 3) if avg_score is not None else None,
        ))

    return segments


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

    machines = [
        {**dict(row), "updated_at": _to_kst(row["updated_at"])}
        for row in rows
    ]
    return MachinesResponse(machines=machines)


# ─────────────────────────────────────────
# GET /machines/{machine_id}
# ─────────────────────────────────────────
@router.get("/machines/{machine_id}", response_model=MachineDetailResponse, summary="머신 상세 + 상태 세그먼트", tags=["머신"])
async def get_machine_detail(machine_id: UUID, period: PeriodEnum, request: Request, ctx: AuthDep):
    conn = request.app.state.pool
    now = datetime.now(timezone.utc)

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

    period_start = now - _PERIOD_DELTA[period]
    bucket_minutes = _PERIOD_BUCKET_MINUTES[period]

    history_rows = await conn.fetch(
        """
        SELECT operational_score, recorded_at
        FROM machine_status_history
        WHERE machine_id = $1
          AND recorded_at > $2
        ORDER BY recorded_at ASC
        """,
        machine_id, period_start,
    )

    segments = _build_segments(history_rows, period_start, bucket_minutes, now)

    machine_data = dict(machine_row)
    machine_data["status_updated_at"] = _to_kst(machine_data.get("status_updated_at"))

    return MachineDetailResponse(
        **machine_data,
        status_segments=segments,
    )
