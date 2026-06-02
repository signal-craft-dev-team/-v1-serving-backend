import os
 
class Settings:
    ENV: str = os.getenv("ENV", "staging")
 
    # 대시보드 origin. 스테이징 배포 시 실제 주소로 잠그세요.
    #   DASHBOARD_ORIGINS="https://dashboard.signalcraft.io,http://localhost:5173"
    DASHBOARD_ORIGINS: list[str] = os.getenv("DASHBOARD_ORIGINS", "*").split(",")
 
    # L1 가동 상태 판정 (시계열 평균)
    OPERATIONAL_WINDOW_POINTS: int = int(os.getenv("OPERATIONAL_WINDOW_POINTS", "10"))
    OPERATIONAL_RUNNING_THRESHOLD: float = float(os.getenv("OPERATIONAL_RUNNING_THRESHOLD", "0.5"))
 
    MAX_SERIES_POINTS: int = 5000  # 시계열 응답 폭주 방지
 
    # 데모용 기본 테넌트. 프로덕션에선 검증된 토큰 클레임에서 주입(아래 deps 참고).
    DEMO_CUSTOMER_ID: str = os.getenv("DEMO_CUSTOMER_ID", "12345678-1234-1234-1234-123456789012")
    DEMO_AUTH_ID: str = os.getenv("DEMO_AUTH_ID", "poc_raven_0001")
    DEMO_AUTH_PROVIDER: str = os.getenv("DEMO_AUTH_PROVIDER", "demo_provider")
 
settings = Settings()