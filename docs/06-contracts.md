# ۰۶ — قرارداد رویداد و API

نسخهٔ 1.0 — پیشوند همهٔ مسیرها: `/api/v1` — تبادل تاریخ: ISO-8601 UTC (`2026-11-11T07:30:00Z`)

## ۱. قرارداد رویداد آموزشی (EVT-01)

`POST /api/v1/events/ingest`
هدرها: `X-Integration-Key: <source key>` · `X-Signature: hex(hmac_sha256(secret, body))` · `X-Timestamp` (±5min)

```json
{
  "event_id": "ev-2026-000123",
  "schema_version": "1.0",
  "source_id": "lms-simulator",
  "university_id": "8f0c…",
  "student_reference": "stu-40123",
  "event_type": "meaningful_attendance_verified",
  "occurred_at": "2026-11-10T09:00:00Z",
  "received_at": "2026-11-10T09:05:12Z",
  "activity_reference": "course/CS101/session/12",
  "evidence_reference": null,
  "verification_status": "verified",
  "correlation_id": "corr-9f31",
  "revision": 1,
  "reference_to_corrected_event": null,
  "payload": {
    "duration_minutes": 90,
    "quality": "normal",
    "course_code": "CS101"
  }
}
```

نوع‌های قراردادی (نگاشت LMS در `docs/06b-lms-mapping.md` همین سند، پایین):
`meaningful_attendance_verified` · `study_completion_verified` · `exercise_assessed` · `adaptive_progress_verified` · `skill_progress_verified` · `contribution_approved` · `peer_support_verified` · `educational_content_approved`

پاسخ‌ها:
- `202` → `{"inbox_state": "validated"|"quarantined", "duplicate": false, "inbox_id": "…", "correlation_id": "…"}`
- تکراری: `202` با `"duplicate": true` — **بدون اثر دوم** (TST-01)
- نامعتبر: `422/401/403` با خطای ساختاریافته یا Quarantine `202` برای خطای نرم (دیررس خارج از پنجره، آیندهٔ نامعتبر)

**نگاشت LMS (Simulator):** درگاه `POST /api/v1/integrations/simulator/lms-webhook` فقط با پرچم آزمایشی کار می‌کند و در `/system/info` با `mode=simulator` اعلام می‌شود. جدول نگاشت مثال: `lecture_attended` (v1, LMS فرضی) → `meaningful_attendance_verified` پس از check-in/close تأیید مدرس.

**خطای ساختاریافته (API-03):**
```json
{"code": "CAPACITY_EXHAUSTED", "message": "ظرفیت این پاداش تکمیل شده است.", "correlation_id": "c-8123", "details": {}}
```

**Idempotency (API-04):** فرمان‌های حساس (`/reward-requests`, `/events/ingest`, `/appeals`, `/data-corrections`) هدر `Idempotency-Key` می‌پذیرند؛ تکرار همان کلید+همان payload ⇒ پاسخ ذخیره‌شده؛ کلید یکسان+payload متفاوت ⇒ `409 IDEMPOTENCY_CONFLICT`.

## ۲. نمونهٔ Request/Response گروه‌های اصلی

| گروه | متد/مسیر | بدنهٔ نمونه | پاسخ نمونه |
| --- | --- | --- | --- |
| auth | `POST /auth/login` | `{"username":"s1@u1.edu","password":"…"}` | `{"access_token":"…","expires_in":900,"user":{...}}` + Set-Cookie `refresh` (HttpOnly, SameSite=Lax, Secure در Prod) |
| auth | `POST /auth/refresh` | cookie | توکن جدید |
| auth-sso | `GET /auth/sso/status` | — | `{"enabled":true,"issuer":"http://188.212.96.235:8086"}` |
| auth-sso | `GET /auth/sso/login` | — | `302` به صفحهٔ ورود سامانهٔ مرکزی دانشجو۳۶۰ (OIDC Authorization Code، state امضاشدهٔ HMAC) |
| auth-sso | `GET /auth/sso/callback?code&state` | — | تبادل کد با token endpoint، هویت فقط از userinfo، تأمین کاربر با نقش پیش‌فرض `student`، Set-Cookie `refresh` و `302` به `/` — خطاها: `302` به `/login?sso_error={state\|token\|userinfo\|upstream\|disabled}` |
| memberships | `POST /memberships/join` | `{"terms_version":"v3","goal_type":"skill","consents":{"personalization":true,"public_badge":false,"notifications":true}}` | `{"membership_state":"active","membership_no":"CLUB-000123"}` |
| consents | `PATCH /consents/{type}` | `{"value":false}` | `{"consent_type":"personalization","value":false,"effective_at":"…"}` |
| goals | `POST /goals` | `{"goal_type":"exam_prep","title_fa":"آمادگی آزمون ریاضی۲"}` | Goal DTO |
| points | `GET /points/summary` | — | `{"available":"24.50","pending":"5.00","reserved":"0.00","cumulative_progress":"132.25","tier":{"path":"learning","level_no":2,"title_fa":"پویا"}}` |
| ledger | `GET /ledger?page=1&page_size=20` | — | `{"items":[{tx DTO}], "total": 42}` — هر آیتم دارای `trace_link` |
| ledger | `GET /ledger/{tx_id}/trace` | — | Calculation Trace کامل (PNT-05) |
| events | `POST /events/self-report` | `{"event_type":"study_completion_verified","activity_reference":"…","evidence_ref":…}` | `{"verification_status":"pending_human"}` (EVT-09) |
| policies | `POST /policies/{code}/versions` → draft | DSL (پایین) | نسخهٔ draft |
| policy-approvals | `POST /policy-approvals` | `{"version_id":"…","decision":"approve","comment":"…"}` | ثبت تأیید دوم |
| simulations | `POST /simulations` | `{"version_id":"…","event_sample":{…}}` | خروجی شبیه‌سازی — **بدون اثر دفترکل** (PNT-07) |
| rewards | `GET /rewards?filter[state]=active` | — | کاتالوگ با ظرفیت/هزینه/شرایط (RWD-02) |
| reward-requests | `POST /reward-requests` | `{"reward_id":"…","idempotency via header"}` | `{"state":"reserved","ttl_expires_at":"…"}` |
| providers | `POST /providers/{id}/callback` | `{"request_ref":"…","result":"confirmed|failed|unknown","receipt":{…},"signature":…}` | `202` |
| recommendations | `GET /recommendations` | — | `{"basis":"consent_personal","items":[{"reward_id":"…","score":0.82,"reasons_fa":["تناسب با هدف «مهارت»","ظرفیت آزاد"]}]}` |
| reviews | `GET /reviews/cases?state=flagged` · `POST /reviews/cases/{id}/decide` | — | گردش doc/05-۷ |
| appeals | `POST /appeals` | `{"case_id":…,"ground_fa":"…"}` | Appeal DTO |
| data-corrections | `POST /data-corrections` | `{"subject":"ledger","reason_fa":"…"}` | درخواست ثبت‌شده |
| notifications | `GET/PATCH /notifications/preferences` · `GET /notifications` | — | NTF |
| analytics | `GET /analytics/overview?period_id=…` | — | شاخص‌های ANA-01 با تعریف/بازه/پوشش + پنهان‌سازی k=5 |
| audit | `GET /audit?entity=policy_versions` | — | AuditLog (نقش حسابرس) |
| jobs | `GET /jobs` · `POST /jobs/{id}/run` | — | Job Status (API-07) |
| system | `GET /system/info` | — | `{"integration_mode":"simulator","queue_backend":"inline","seed_label":"demo","policy_signoff":false}` |
| ops | `GET /healthz` · `GET /readyz` · `GET /metrics` | — | liveness/readiness/متن PromQL |

**Pagination امن (API-02):** `page`، `page_size ≤ 100`، `sort` فقط از allowlist ستون‌ها، `filter[field]=…` با allowlist.

## ۳. DSL سیاست (PNT-01/02) — نمونهٔ نسخهٔ منتشرشده

```json
{
  "rule_id": "attendance_base_v1",
  "event_type": "meaningful_attendance_verified",
  "evidence_required": false,
  "conditions": {"all": [
    {"field": "payload.duration_minutes", "op": ">=", "value": 45}
  ]},
  "base_points": "10.00",
  "quality_multiplier": {"field": "payload.quality", "map": {"high": "1.20", "normal": "1.00", "low": "0.80"}, "default": "1.00"},
  "progress_multiplier": {"default": "1.00"},
  "repeat_policy": {"window_days": 7, "diminishing": ["1.00", "0.50", "0.25"], "beyond": "0"},
  "caps": {"per_day": "30.00", "per_period": "300.00"},
  "exclusive_group": "attendance",
  "late_policy": {"max_late_hours": 72, "factor": "1.00"},
  "human_reason_template": "حضور معنادار تأییدشده در {activity_reference}"
}
```
عملگرهای مجاز: `== != > >= < <= in not_in between` — مقادیر فقط ثابت؛ **هیچ eval/Python/SQL دلخواه** (PNT-02). ارزیابی خالص و قطعی است و `RuleEvaluation` با Trace کامل می‌سازد.

## ۴. Webhook ارائه‌دهندهٔ خارجی (RWD-06)

`POST /api/v1/providers/{provider_id}/callback` با امضای HMAC؛ `result ∈ {confirmed, failed, unknown}`؛ `unknown` ⇒ `ReconciliationCase` — **استرداد خودکار ممنوع** (TST-09).
