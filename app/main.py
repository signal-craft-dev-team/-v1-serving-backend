from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .src.config import settings
from .src.database.db import init_pool
from .src.routers import me, machines, places


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.pool = await init_pool(settings.DATABASE_URL)
    yield
    await app.state.pool.close()


app = FastAPI(
    title="SignalCraft Serving API (staging)",
    version="0.0.1",
    description="""스테이징 서버.<br>
                  대시보드 연동용.<br>
                  헤더 예시:<br>
                  - X-Auth-Provider: demo_provider<br>
                  - X-Auth-Id: poc_raven_0001<br>
                  - X-Customer-ID: 12d5e33c-405a-4856-bf8e-51fc899c1737<br>
                  - place_id: b33f995b-0e79-4551-afc4-e0c79238a18a
                  """,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.DASHBOARD_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me.router)
app.include_router(machines.router)
app.include_router(places.router)


@app.get("/health", tags=["meta"], summary="헬스 체크")
async def health():
    return {"status": "ok", "version": app.version, "env": settings.ENV}
