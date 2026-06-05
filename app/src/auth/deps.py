"""
인증 의존성 — 헤더 기반 하드코딩 방식 (스테이징)

X-Auth-Provider + X-Auth-Id 로 app_user 조회
X-Customer-ID 로 소속 고객사 검증

프로덕션 전환 시 이 파일만 JWT 검증으로 교체하면 됨.
"""
from typing import Annotated
from uuid import UUID
from fastapi import Header, HTTPException, Depends, Request
from pydantic import BaseModel


class UserContext(BaseModel):
    user_id: UUID
    customer_id: UUID
    email: str
    name: str
    role: str

class CustomerContext(BaseModel):
    customer_id: UUID
    name: str
    is_active: bool


async def get_customer_context(
    request: Request,
    x_auth_provider: Annotated[str, Header()],
    x_auth_id: Annotated[str, Header()],
    x_customer_id: Annotated[str, Header()],
) -> CustomerContext:
    conn = request.app.state.pool

    # 추후 앱 유저 생성시 사용
    # try:
    #     customer_uuid = UUID(x_customer_id)
    # except ValueError:
    #     raise HTTPException(status_code=400, detail="X-Customer-ID 형식이 올바르지 않습니다.")

    # user = await conn.fetchrow(
    #     """
    #     SELECT id, customer_id, email, name, role
    #     FROM app_user
    #     WHERE external_auth_provider = $1
    #       AND external_auth_id = $2
    #       AND is_active = true
    #     """,
    #     x_auth_provider, x_auth_id,
    # )

    # if not user:
    #     raise HTTPException(status_code=401, detail="인증 정보를 찾을 수 없습니다.")

    # if user["customer_id"] != customer_uuid:
    #     raise HTTPException(status_code=403, detail="X-Customer-ID 가 일치하지 않습니다.")

    # return UserContext(
    #     user_id=user["id"],
    #     customer_id=user["customer_id"],
    #     email=user["email"],
    #     name=user["name"],
    #     role=user["role"],
    # )
    
    # 하드코딩 값으로 임시 진행(스테이징용)
    try:
        if not x_customer_id:
            raise HTTPException(status_code=400, detail="X-Customer-ID 헤더가 필요합니다.")
        if not x_auth_provider:
            raise HTTPException(status_code=400, detail="X-Auth-Provider 헤더가 필요합니다.")
        if not x_auth_id:
            raise HTTPException(status_code=400, detail="X-Auth-Id 헤더가 필요합니다.")
        
        if x_auth_provider != "demo_provider" or x_auth_id != "poc_raven_0001":
            raise HTTPException(status_code=401, detail="인증 정보가 유효하지 않습니다.")
        
        customer_uuid = UUID(x_customer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Customer-ID 형식이 올바르지 않습니다.")
    except Exception as e:
        raise e
    
    customer = await conn.fetchrow(
        """
        SELECT id, name, is_active
        FROM customer
        WHERE id = $1
        """,
        customer_uuid,
    )
    if not customer:
        raise HTTPException(status_code=403, detail="X-Customer-ID 가 유효하지 않습니다.")
    
    if customer["is_active"] != True:
        raise HTTPException(status_code=403, detail="소속 고객사가 비활성화 상태입니다.")

    return CustomerContext(
        customer_id=customer_uuid,
        name=customer["name"],
        is_active=customer["is_active"],
    )


AuthDep = Annotated[CustomerContext, Depends(get_customer_context)]
