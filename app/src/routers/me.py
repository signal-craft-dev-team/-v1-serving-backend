from uuid import UUID
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from ..auth.deps import AuthDep

router = APIRouter()


class UserInfo(BaseModel):
    id: UUID
    email: str
    name: str
    phone: str
    role: str = Field(..., examples=["admin", "manager", "viewer"])
    is_active: bool


class CustomerInfo(BaseModel):
    id: UUID
    name: str
    is_active: bool


class PlaceInfo(BaseModel):
    id: UUID
    name: str = Field(..., examples=["A공장"])
    sub_name: str | None = None
    address: str | None = None
    is_active: bool


class TechnicianInfo(BaseModel):
    id: UUID
    name: str
    phone: str
    address: str
    is_primary: bool
    is_active: bool


class MeResponse(BaseModel):
    user: UserInfo
    customer: CustomerInfo
    places: list[PlaceInfo]
    technicians: list[TechnicianInfo]


@router.get("/me", response_model=MeResponse, summary="사용자 컨텍스트 조회", tags=["고객사"])
async def get_me(request: Request, ctx: AuthDep):
    conn = request.app.state.pool

    # # 사용자 상세
    # user_row = await conn.fetchrow(
    #     "SELECT id, email, name, phone, role, is_active FROM app_user WHERE id = $1",
    #     ctx.user_id,
    # )

    # 고객사
    customer_row = await conn.fetchrow(
        "SELECT id, name, is_active FROM customer WHERE id = $1",
        ctx.customer_id,
    )

    # 현장 목록
    place_rows = await conn.fetch(
        "SELECT id, name, sub_name, address, is_active FROM place WHERE customer_id = $1 AND is_active = true ORDER BY name",
        ctx.customer_id,
    )

    # 정비사 목록 (customer_technician 조인)
    technician_rows = await conn.fetch(
        """
        SELECT t.id, t.name, t.phone, t.address, t.is_active, ct.is_primary
        FROM customer_technician ct
        JOIN technician t ON ct.technician_id = t.id
        WHERE ct.customer_id = $1 AND t.is_active = true
        ORDER BY ct.is_primary DESC, t.name
        """,
        ctx.customer_id,
    )

    return MeResponse(
        # user=UserInfo(**dict(user_row)),
        user=UserInfo(
            id=UUID(int=0),
            email="",
            name="",
            phone="",
            role="viewer",
            is_active=True,
        ),
        customer=CustomerInfo(**dict(customer_row)),
        places=[PlaceInfo(**dict(r)) for r in place_rows],
        technicians=[TechnicianInfo(**dict(r)) for r in technician_rows],
    )
