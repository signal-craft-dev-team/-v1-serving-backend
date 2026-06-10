# SignalCraft Serving API 가이드

> 버전: v0.0.1 (staging)
> Base URL: `https://v1.api.stag.serving.signalcraft.kr`

---

## 인증 (공통 헤더)

모든 엔드포인트에 아래 3개 헤더가 필요합니다.

| 헤더 | 타입 | 설명 | 예시 |
|---|---|---|---|
| `X-Auth-Provider` | string | 인증 제공자 식별자 | `demo_provider` |
| `X-Auth-Id` | string | 인증 제공자의 사용자 ID | `poc_raven_0001` |
| `X-Customer-ID` | UUID | 고객사 UUID | `12d5e33c-405a-4856-bf8e-51fc899c1737` |
| `place_id` | UUID | 고객사 장소 UUID | `b33f995b-0e79-4551-afc4-e0c79238a18a` |

**인증 실패 응답:**

| 상태 코드 | 원인 |
|---|---|
| `400` | 헤더 누락 또는 UUID 형식 오류 |
| `401` | X-Auth-Provider / X-Auth-Id 불일치 |
| `403` | X-Customer-ID가 DB에 없거나 비활성화 상태 |

---

## 엔드포인트 목록

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 헬스 체크 |
| GET | `/me` | 사용자 컨텍스트 (고객사 / 현장 / 정비사) |
| GET | `/machines` | 고객사 전체 머신 현재 상태 목록 |
| GET | `/machines/{machine_id}` | 특정 머신 상세 + 상태 이력 |
| GET | `/places/{place_id}/machines` | 특정 현장의 머신 목록 |

---

## GET /health

서버 상태 확인. 인증 헤더 불필요.

**Response `200`**
```json
{
  "status": "ok",
  "version": "0.0.1",
  "env": "staging"
}
```

---

## GET /me

대시보드 초기 로딩 시 사용. 인증된 사용자의 고객사 컨텍스트 전체를 한번에 반환합니다.

> **현재 스테이징**: `user` 필드는 OAuth 연동 전이므로 빈 값으로 반환됩니다.

**Response `200`**
```json
{
  "user": {
    "id": "00000000-0000-0000-0000-000000000000",
    "email": "",
    "name": "",
    "phone": "",
    "role": "viewer",
    "is_active": true
  },
  "customer": {
    "id": "12d5e33c-405a-4856-bf8e-51fc899c1737",
    "name": "레이븐머티리얼즈",
    "is_active": true
  },
  "places": [
    {
      "id": "b33f995b-0e79-4551-afc4-e0c79238a18a",
      "name": "레이븐머티리얼즈",
      "sub_name": "연구소",
      "address": "인천 남동구 남동대로215번길 93",
      "is_active": true
    }
  ],
  "technicians": [
    {
      "id": "f95d95ab-08c5-4cae-acd3-8b96641305fe",
      "name": "이레테크",
      "phone": "042-627-9609",
      "address": "대전광역시 동구 하소로 43",
      "is_primary": true,
      "is_active": true
    }
  ]
}
```

**필드 설명**

| 필드 | 타입 | 설명 |
|---|---|---|
| `user.role` | string | `admin` \| `manager` \| `viewer` |
| `places` | array | `is_active=true`인 현장만 반환, 이름 오름차순 |
| `technicians` | array | `is_active=true`인 정비사만 반환, `is_primary=true` 우선 정렬 |
| `technicians[].is_primary` | bool | 해당 고객사의 메인 정비사 여부 |

---

## GET /machines

고객사에 속한 **활성 머신 전체**의 현재 상태를 반환합니다. `machine_code` 오름차순 정렬.

**Response `200`**
```json
{
  "machines": [
    {
      "machine_id": "33333333-3333-3333-3333-333333333331",
      "machine_code": "sk-pump-0001ab",
      "label": "A공장 펌프",
      "operational_state": "running",
      "operational_score": 0.95,
      "current_state": "normal",
      "remaining_score": null,
      "active_alerts_count": 0,
      "sensor_online": true,
      "updated_at": "2026-06-05T07:30:00Z"
    }
  ]
}
```

**필드 설명**

| 필드 | 타입 | 설명 |
|---|---|---|
| `machine_id` | UUID | 머신 고유 ID |
| `machine_code` | string | 외부 노출용 기기 코드 (예: `sk-pump-0001ab`) |
| `label` | string \| null | 표시 이름. 없으면 `machine_code`로 대체 권장 |
| `operational_state` | enum | 운영 상태 (L1). 아래 Enum 참조 |
| `operational_score` | float \| null | 가동 확률 `0.0~1.0`. 데이터 없으면 `null` |
| `current_state` | enum | 건강 상태 (L2). 아래 Enum 참조 |
| `remaining_score` | float \| null | 잔여 수명 점수. ML 고도화 후 제공 예정 |
| `active_alerts_count` | int | 미해결 알람 수 |
| `sensor_online` | bool | 최근 10분 이내 센서 하트비트 수신 여부 |
| `updated_at` | datetime \| null | 상태 마지막 갱신 시각. 데이터 없으면 `null` |

---

## GET /machines/{machine_id}

특정 머신의 현재 상태 + 지정 기간 내 상태 이력을 반환합니다.

**Path Parameter**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `machine_id` | UUID | 머신 ID |

**Query Parameter**

| 파라미터 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `period` | enum | ✅ | 이력 조회 기간. `24h` \| `3d` \| `5d` \| `7d` |

**Response `200`**
```json
{
  "machine_id": "33333333-3333-3333-3333-333333333331",
  "machine_code": "sk-pump-0001ab",
  "label": "A공장 펌프",
  "place_id": "b33f995b-0e79-4551-afc4-e0c79238a18a",
  "operational_state": "running",
  "operational_score": 0.95,
  "current_state": "normal",
  "remaining_score": null,
  "active_alerts_count": 0,
  "sensor_online": true,
  "status_updated_at": "2026-06-05T07:30:00Z",
  "machine_status_history": [
    {
      "id": "77777777-7777-7777-7777-777777777771",
      "operational_state": "running",
      "operational_score": 0.95,
      "current_state": "normal",
      "recorded_at": "2026-06-05T07:20:00Z"
    },
    {
      "id": "77777777-7777-7777-7777-777777777772",
      "operational_state": "running",
      "operational_score": 0.88,
      "current_state": "warning",
      "recorded_at": "2026-06-05T07:10:00Z"
    }
  ]
}
```

**필드 설명 (추가)**

| 필드 | 타입 | 설명 |
|---|---|---|
| `place_id` | UUID | 머신이 설치된 현장 ID |
| `status_updated_at` | datetime \| null | 현재 상태 마지막 갱신 시각 |
| `machine_status_history` | array | `recorded_at` 내림차순. 최대 5,000건 |
| `machine_status_history[].id` | UUID | 이력 레코드 ID |
| `machine_status_history[].recorded_at` | datetime | 이 상태가 기록된 시각 |

**Response `404`**
```json
{ "detail": "해당 머신을 찾을 수 없습니다." }
```

---

## GET /places/{place_id}/machines

특정 현장에 설치된 **활성 머신 목록**과 현재 상태를 반환합니다.

**Path Parameter**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `place_id` | UUID | 현장 ID (`/me` 응답의 `places[].id`) |

**Response `200`**
```json
{
  "place_id": "b33f995b-0e79-4551-afc4-e0c79238a18a",
  "machines": [
    {
      "machine_id": "33333333-3333-3333-3333-333333333331",
      "machine_code": "sk-pump-0001ab",
      "label": "A공장 펌프",
      "operational_state": "running",
      "operational_score": 0.95,
      "current_state": "normal",
      "remaining_score": null,
      "active_alerts_count": 0,
      "sensor_online": true,
      "updated_at": "2026-06-05T07:30:00Z"
    }
  ]
}
```

**Response `404`**
```json
{ "detail": "해당 현장을 찾을 수 없습니다." }
```

---

## Enum 값 정의

### operational_state (운영 상태, L1)

| 값 | 설명 | 대시보드 표시 권장 |
|---|---|---|
| `running` | 가동 중 | 🟢 ON |
| `stopped` | 정지 중 | ⚫ OFF |
| `error` | 오류 상태 | 🔴 ERROR |
| `unknown` | 데이터 없음 (초기값) | ⚪ — |

### current_state (건강 상태, L2)

| 값 | 설명 | 대시보드 표시 권장 |
|---|---|---|
| `unknown` | 첫 추론 전 또는 데이터 없음 | ⚪ — |
| `normal` | 정상 | 🟢 정상 |
| `warning` | 주의 (임계값 근접) | 🟡 주의 |
| `abnormal` | 이상 감지 | 🟠 이상 |
| `critical` | 심각 이상 | 🔴 위험 |
| `offline` | 센서/서버 통신 두절 | ⚫ 오프라인 |

---

## 권장 대시보드 호출 패턴

```
1. 앱 초기화
   GET /me
   → 고객사, 현장 목록, 정비사 정보 캐싱

2. 머신 대시보드 진입
   GET /machines
   → 전체 머신 상태 카드 렌더링

3. 특정 현장 필터
   GET /places/{place_id}/machines
   → 현장별 머신 목록

4. 특정 머신 클릭
   GET /machines/{machine_id}?period=24h
   → 상태 이력 차트 렌더링

5. 주기적 갱신 (폴링)
   GET /machines  또는  GET /places/{place_id}/machines
   → 1~10분 간격 권장
```
