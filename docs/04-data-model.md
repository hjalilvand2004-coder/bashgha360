# ۰۴ — مدل داده (ERD) و قیود

نسخهٔ 1.0 — پیاده‌سازی واقعی: `backend/app/modules/*/models.py` + Migration `alembic/versions/0001_initial.py`
همهٔ جداول دامنه: `id UUID PK (gen_random_uuid)`, `university_id UUID FK→universities` (مگر مرجع سراسری)، `created_at/updated_at TIMESTAMPTZ` (UTC)، `source` و `retention_class` برای سیاست نگهداری.

## ۱. فهرست موجودیت‌ها به تفکیک ماژول

### identity_access
| جدول | فیلدهای کلیدی | قیدهای مهم |
| --- | --- | --- |
| universities | code UNIQUE, name_fa, timezone (پیش‌فرض Asia/Tehran), settings JSONB | — |
| users | national_ref UNIQUE NULLS DISTINCT per university, display_name, email, phone, password_hash NULL, identity_mode(local|sso), totp_secret NULL, is_active | uq(university_id, lower(email)) |
| roles | code UNIQUE, name_fa, permissions TEXT[] | allowlist permission در کد |
| user_role_scopes | user FK, role FK, university_id, department NULL, expires_at NULL, granted_by, is_emergency BOOL | idx(user, university) |
| student_references | user FK NULL, external_student_id, university_id, program, entry_year | uq(university_id, external_student_id) |
| sessions | user FK, refresh_hash UNIQUE, expires_at, revoked_at NULL, user_agent, ip_masked | idx(user) |
| auth_audit | user NULL, event, ip_masked, detail JSONB | append-only |

### memberships_consents
| جدول | نکته |
| --- | --- |
| terms_versions | version_no, content_fa TEXT, published_at, is_current؛ انتشار تأییددوم |
| memberships | student_ref FK, state (ماشین حالت ۱ doc/05), joined_at, terms_version FK, left_at NULL؛ uq(student_ref) |
| consent_records | student_ref, consent_type(personalization|public_badge|notifications), value BOOL, terms_version FK, decided_at, revoked_effective_at؛ index(student_ref, consent_type, decided_at) |
| advisor_assignments | advisor FK, student_ref FK, university_id, scope_note؛ uq |
| approval_scopes | professor FK, course_code/activity_scope, period FK؛ برای ACC-04 |

### student_goals
| جدول | نکته |
| --- | --- |
| academic_periods | university, title_fa, starts_at, ends_at, is_current؛ مرز ترم با tz دانشگاه |
| student_goals | student_ref, goal_type(weakness|exam_prep|skill|collaboration|other), title_fa, status, period FK؛ uq فعال یک هدف از هر نوع |
| data_correction_requests | requester, subject_entity, subject_id, reason, state (doc/05-۱۲), decision_note |

### event_ingestion
| جدول | قید |
| --- | --- |
| integration_sources | code, name_fa, university FK, auth_mode(hmac|service_key), secret_ref, rate_limit_per_min, is_active, is_simulator BOOL | uq(university, code) |
| educational_events | **غیرقابل تغییر (trigger)**؛ event_id, schema_version, source FK, student_reference, event_type, occurred_at, received_at, activity_reference, evidence_reference NULL, verification_status(pending_human|verified|rejected), correlation_id, revision INT, reference_to_corrected_event NULL, payload JSONB محدود؛ **uq(university_id, source_id, event_id)** | idx(event_type, occurred_at) |
| event_corrections | correction FK→educational_events, target FK→educational_events, reason | — |
| evidence_references | kind, uri privado (S3 key), hash, uploaded_by, expires_at | uri هرگز URL عمومی نیست |
| event_inbox | message_id, event FK, state (doc/05-۳), attempts, last_error, next_retry_at, quarantined_reason NULL؛ uq(message_id) |

### policy_engine
| جدول | قید |
| --- | --- |
| policies | code UNIQUE per university, title_fa, exclusive_group NULL, priority INT | |
| policy_versions | policy FK, version_no, status(draft…retired), dsl JSONB (اعتبارسنجی RuleSpec در کد), effective_from, effective_to NULL, late_window_hours, requires_evidence BOOL, created_by, approved_at/by NULL, approval_ref NULL؛ **uq(policy, version_no)**؛ published قفل |
| policy_approvals | version FK, approver FK, decided_at, comment؛ uq(version, approver)؛ requester≠approver در سرویس |
| rule_simulations | version FK, input JSONB, output JSONB, ran_by؛ بدون اثر عملیاتی |
| rule_evaluations | event FK, version FK, student_ref, conditions_result JSONB, effective_inputs JSONB, caps_applied JSONB, rounding, final_points NUMERIC(14,2), human_reason_fa, tx FK NULL | idx(event) |
| policy_cap_usage | student_ref, version FK, window_key TEXT (day/period/activity), used NUMERIC؛ **uq(student_ref, version, window_key)** — قفل ردیف برای enforce هم‌زمانی |

### points_ledger
| جدول | قید |
| --- | --- |
| point_accounts | student_ref FK؛ available/reserved/pending NUMERIC(14,2) DEFAULT 0؛ cumulative_progress NUMERIC(14,2)؛ spent_total/expired_total؛ **CHECK available≥0 AND reserved≥0 AND pending≥0**؛ uq(student_ref) |
| ledger_transactions | tx_type, status(committed|reversed), idempotency_key NULL؛ **uq جزئی (idempotency_key) WHERE NOT NULL**؛ event FK NULL, version FK NULL, reward_request FK NULL, case FK NULL, actor, reason_fa؛ correction_of FK NULL (سند جبرانی) |
| ledger_entries | tx FK, account FK, direction(debit|credit), bucket, amount>0, balance_after, rule_version FK NULL, reference | **append-only (trigger)**؛ idx(tx) idx(account) |
| balance_projections | account FK, as_of, available, reserved, pending, cumulative؛ بازسازی‌پذیر از entries |
| progress_records | student_ref, metric(learning_streak|skill_growth|collaboration), value, baseline_value, baseline_type(own_baseline), period FK؛ PRN-03 |

### achievements_tiers
| جدول | نکته |
| --- | --- |
| tier_definitions | path(learning|skill|collaboration), level_no, title_fa, min_progress, icon_svg_id؛ مرجع سراسری قابل کپی per university |
| tier_awards | student_ref, tier FK, awarded_at, tx FK NULL؛ uq(student_ref, tier) |
| badge_definitions | title_fa, svg_id, path, criteria JSONB, criteria_version, issuer_fa, valid_months, is_auto |
| badge_awards | student_ref, badge FK, issued_at, expires_at NULL, state(valid|corrected|revoked), reason_fa NULL, evidence_ref NULL؛ uq(student_ref, badge, issued_at::date) |
| badge_shares | award FK, share_token UNIQUE, created_by student, revoked_at NULL, expires_at NULL |

### missions_groups
| جدول | نکته |
| --- | --- |
| missions | title_fa, goal_type, activities JSONB, success_criteria JSONB, window(starts/ends), reward_ref NULL, max_points, alternative_path_fa NULL, is_group BOOL |
| mission_participations | mission FK, student_ref, state(doc/05-۹), joined_at, ended_at NULL؛ uq(mission, student_ref) |
| learning_groups | mission FK, title_fa, capacity؛ group_members(uq(group, student_ref), consent_at) |
| group_contributions | group FK, member, share_note, evidence_ref, approved_by, points_tx FK NULL؛ جلوگیری از امتیاز تکراری: uq(group, member, activity_key) |

### rewards_fulfillment
| جدول | قید |
| --- | --- |
| reward_providers | name_fa, contact_ref, callback_secret_ref, university FK, is_active |
| rewards | provider FK NULL(درون‌سامانه‌ای NULL), type (۸ نوع doc RWD-01), title_fa, description_fa, cost_points, capacity_total NULL (NULL=نامحدود), allocation(first_come|quota|queue|lottery), delivery(in_app|code|external), conditions JSONB (رشته/مهارت/زمان/دسترس‌پذیری), is_essential BOOL CHECK(NOT is_essential OR cost_points=0), validity, refund_policy_fa, data_consent_note NULL, state(active|paused) |
| reward_capacities | reward FK, window(starts/ends), total, reserved_count, final_count؛ قفل ردیف |
| reward_requests | student_ref, reward FK, state(doc/05-۶), requested_at, decided_by/at NULL, cancel_reason, ttl_expires_at؛ uq جزئی (student_ref, reward, active_states) WHERE state IN active |
| reward_reservations | request FK, capacity FK NULL, points_tx FK, expires_at, released_at NULL |
| fulfillment_attempts | request FK, attempt_no, state(doc/05-۱۰), sent_at, result_at, detail |
| delivery_receipts | request FK UNIQUE, one_time_code_hash, issued_at, consumed_at NULL, receipt_fa JSONB |
| reconciliation_cases | request FK, detected_at, provider_report, resolution |

### recommendations
| جدول | نکته |
| --- | --- |
| recommendation_runs | student_ref NULL(عمومی), basis(consent_personal|generic), inputs_snapshot JSONB, recommender_version, rule_pack_version |
| recommendation_items | run FK, reward FK, score NUMERIC, reasons_fa TEXT[], rank |
| recommendation_feedback | item FK, student_ref, feedback(like|dismiss|not_now), note NULL |

### integrity_reviews
| جدول | نکته |
| --- | --- |
| integrity_signals | kind(deterministic|risk_pattern), rule_code, severity, subject_student NULL, refs JSONB, is_advisory BOOL |
| review_cases | signal FK, student_ref, state(doc/05-۷), opened_at, sla_due_at, assigned_to NULL, decided_by/at NULL, summary_fa (متن دانشجویی) |
| case_explanations | case FK, student_ref, body, submitted_at |
| case_decisions | case FK, decision(cleared|violation_minor|violation_major|refer_official), justification_fa, affected_tx FK NULL, decided_by |

### appeals
| جدول | نکته |
| --- | --- |
| appeals | case FK NULL, request FK NULL (اعتراض به تصمیم/اصلاح/عدم تخصیص), student_ref, ground_fa, state(doc/05-۸), reviewer FK (≠ بررسی‌کنندهٔ اولیه), decision_fa NULL, decided_at |
| appeal_outcomes | appeal FK, ledger_tx FK NULL (سند جبرانی), badge/tier recalc BOOL |

### notifications
| جدول | نکته |
| --- | --- |
| notification_prefs | student_ref UNIQUE, channels JSONB, quiet_hours, daily_cap, mute_until |
| notifications | user FK, kind (۶ نوع)، transactional BOOL, channel, payload حداقلی بدون دادهٔ حساس, state(doc/05-۱۱), attempts, sent_at NULL |
| outbox_messages | aggregate, payload JSONB, state(pending|dispatched|failed), available_at, attempts؛ مصرف‌کننده: worker |
| background_jobs | job_type, payload, state, run_at, attempts, last_error؛ Job Status API |

### audit
| جدول | نکته |
| --- | --- |
| audit_logs | actor NULL, action, entity, entity_id, before/after JSONB, university_id, correlation_id, ip_masked؛ **append-only trigger**؛ بدون PII حساس (masked) |
| retention_policies | entity, keep_months, action(anonymize|delete), approved_ref |
| anonymization_log | subject, done_at, scope؛ جداسازی هویت از حسابرسی (DM-04) |

## ۲. ناوردایی‌های سطح DB

1. `CHECK` موجودی‌های غیرمنفی روی `point_accounts`.
2. `UNIQUE NULLS NOT DISTINCT`-معادل: ایندکس جزئی روی `ledger_transactions(idempotency_key)` و `reward_requests` فعال.
3. `CONSTRAINT TRIGGER DEFERRABLE` توازن هر `ledger_transactions` (Σdebit=Σcredit) در COMMIT.
4. Trigger بی‌ردپا (REJECT) روی UPDATE/DELETE برای `ledger_entries`, `audit_logs`, `educational_events`, `auth_audit`.
5. FKها همه با `ON DELETE RESTRICT` (حذف مولد ممنوع)؛ حذف PII فقط با مسیر ناشناس‌سازی مصوب.
6. ایندکس‌های پرس‌وجوی داغ: `(university_id, event_type, occurred_at)`, `(account_id, id)`, `(student_ref, state)` روی reward_requests، `(state, next_retry_at)` روی inbox/outbox.

## ۳. سیاست نگهداری (پیش‌فرض — قابل نسخه‌گذاری)

| داده | نگهداری | اقدام پس از آن |
| --- | --- | --- |
| ledger/audit | دائمی (الزام حسابرسی) — بدون ویرایش | — |
| educational_events (payload) | ۳۶ ماه | ناشناس‌سازی student_reference |
| notifications | ۱۲ ماه | حذف |
| sessions/auth_audit | ۲۴ ماه | حذف/ناشناس |
| recommendation snapshots | ۱۸ ماه | حذف |
| review_cases | ۶۰ ماه | ناشناس‌سازی |
