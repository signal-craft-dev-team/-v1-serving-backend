from uuid import UUID
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from ..auth.deps import AuthDep
from .machines import MachineStatus, OperationalState, MachineState

router = APIRouter()


class PlaceMachinesResponse(BaseModel):
    place_id: UUID
    machines: list[MachineStatus]


@router.get("/places/{place_id}/machines", response_model=PlaceMachinesResponse, summary="현장별 머신 목록", tags=["현장"])
async def get_machines_by_place(place_id: UUID, request: Request, ctx: AuthDep):
    conn = request.app.state.pool

    place = await conn.fetchval(
        "SELECT id FROM place WHERE id = $1 AND customer_id = $2",
        place_id, ctx.customer_id,
    )
    if not place:
        raise HTTPException(status_code=404, detail="해당 현장을 찾을 수 없습니다.")

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
        WHERE m.place_id = $1
          AND m.customer_id = $2
          AND m.is_active = true
        ORDER BY m.machine_code
        """,
        place_id, ctx.customer_id,
    )

    return PlaceMachinesResponse(
        place_id=place_id,
        machines=[dict(row) for row in rows],
    )
