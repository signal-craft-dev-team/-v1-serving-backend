from typing import Annotated
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from uuid import UUID
 
from .src.config import settings
# # 모델
# from user_models import MeResponse, UserInfo, CustomerInfo, PlaceInfo, TechnicianInfo
# from machine_models import (MachinesResponse, MachineStatus, MachineDetailResponse,
#                              MachineStatusHistoryPoint, OperationalState, MachineState, PeriodEnum)

# --------------------------------------------------------------------------
# App
# --------------------------------------------------------------------------
app = FastAPI(
    title="SignalCraft API (staging)",
    version="0.0.1",
    description='''스테이징 서버.<br>
                  ON/OFF(L1) 검증 + 대시보드 연동용.<br>
                  스테이징 상태에서 다음 값 참조 요망<br>
                  - X-Auth-Id: poc_raven_0001<br>
                  - X-Auth-Provider: demo_provider<br>
                  - X-Customer-ID: 12345678-1234-1234-1234-123456789012''',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.DASHBOARD_ORIGINS,   # 스테이징에선 대시보드 origin 으로 잠그세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
