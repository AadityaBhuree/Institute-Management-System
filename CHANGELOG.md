# Changelog

All notable changes to the **Institute Management System (IMS Enterprise)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.8.0] - 2026-11-25

### Added
- **Real-Time Server-Sent Events (SSE) Live Notification Feeds & Telemetry Streaming (Phase 16)**:
  - **In-Process Pub/Sub Event Broker (`src/core/event_broker.py`)**:
    - Thread-safe, cross-thread publish/subscribe event routing with `Subscriber` dataclass, bounded `asyncio.Queue` channels (maxsize 100), and automated queue overflow eviction preventing memory leaks.
    - Role-based audience filtering (`ALL`, `ADMIN`, `FACULTY`, `STUDENT`) and user-specific targeting (`target_user_id`).
    - Standard W3C Server-Sent Events protocol serialization with event names, unique IDs, structured JSON payloads, and keepalive heartbeat comments (`: ping\n\n`).
  - **Streaming REST & SSE API Endpoints**:
    - `GET /api/notifications/stream`: Authenticated live SSE notification feed for scholars, faculty, and administrators yielding immediate connection handshakes (`event: connected`) and live targeted alerts. Supports both cookie/Bearer session tokens and native browser `?token=` query parameter authentication.
    - `GET /api/system/telemetry/stream` (Admin only): Live real-time operational telemetry and audit stream yielding initial system diagnostics snapshots (`event: telemetry_snapshot`), periodic heartbeats with background task queue metrics and broker statistics, and immediate security audit events (`event: audit_log`).
  - **Automated Domain Service Real-Time Event Dispatches**:
    - `NotificationService.create`: Automatically publishes `notification` events over the `notifications` channel to all active subscribers matching the target role and user ID.
    - `FinanceService.record_payment`: Automatically dispatches in-app notification and real-time SSE payment receipt notices to the scholar and bursar.
    - `LeaveService.update_status`: Automatically dispatches in-app notification and real-time SSE decision notices upon approval or rejection of student/faculty leave petitions.
    - `AuthService.log_audit`: Automatically streams security audit records to the `telemetry` channel for connected admin dashboards.
  - **High-Performance Pure ASGI Middleware (`src/core/security_hardening.py`)**:
    - Refactored `SecurityHeadersMiddleware` and `RequestBodySizeLimitMiddleware` from `BaseHTTPMiddleware` to pure ASGI middlewares (`__call__(scope, receive, send)`), eliminating Starlette response buffering and enabling zero-latency chunk streaming.
  - **Frontend UI Real-Time EventSource Integration**:
    - `static/js/app.js`: Added `initLiveSSEFeeds()` runtime subscribing to `/api/notifications/stream`, rendering toast notifications with priority-based styling (`URGENT`, `HIGH`, `NORMAL`), dynamically updating the unread notification badge counter, and automatically reconnecting with backoff.
    - `templates/base.html`: Added real-time notification badge indicator (`#alerts-unread-counter`) to the header Alerts button and a live connection indicator dot (`#live-status-dot`) to the sidebar footer.
  - Maintained core application decoupling with `src/app.py` preserved at exactly **121 lines** (<150 lines target).
- **Automated Testing Suite Expansion**:
  - Added comprehensive test suite `tests/test_live_events_and_sse.py` containing 14 unit and integration tests covering subscription lifecycles, role/user filtering, queue overflow protection, cross-thread dispatches, query token authentication, RBAC boundaries, and domain service event triggers.
  - Expanded test suite from 306 to **320 automated tests** passing across 29 domain test suites (100% pass rate in 11.63s).

---

## [1.7.0] - 2026-11-23

### Added
- **Multi-Format Reporting Engine & Cohort Archival Subsystem (Phase 15)**:
  - **Native Vector PDF Document Generator (`src/services/pdf_service.py`)**:
    - Programmatic A4 vector PDF compilation via `reportlab` with custom canvas watermark callbacks, running footers with timestamps and page numbers, and institutional styling.
    - Sealed academic transcripts (`generate_transcript_pdf`) featuring student demographics, enrolled course assessments, GPA calculations, and registrar signature block.
    - Official bursar fee receipts (`generate_fee_receipt_pdf`) featuring invoice breakdown, payment transaction history, and verified payment stamp.
    - Clinical medical clearance certificates (`generate_medical_certificate_pdf`) with patient details, diagnosis, rest period, and physician sign-off.
  - **Streaming Excel (.xlsx) Data Exporter (`src/services/excel_service.py`)**:
    - High-performance workbook compilation using `openpyxl` with dynamic column auto-widths, navy/teal headers, thin borders, zebra-striped data rows, and frozen panes.
    - Master scholar directory export (`export_students_excel`).
    - Multi-tab financial ledger workbook (`export_finances_excel`) featuring invoices ledger with formatted currency numbers and departmental recovery rate matrix.
    - Multi-tab attendance workbook (`export_attendance_excel`) with conditional risk highlighting (<75%) and institutional telemetry overviews.
  - **Policy-Driven Cohort Archival & Cold Storage (`src/services/archival_service.py`)**:
    - Added database migration `src/database/migrations/007_cohort_archival.sql` and updated `src/database/schema.sql` creating `archived_students` table.
    - Automated graduation cohort archival with deterministic JSON dossier snapshots and SHA-256 cryptographic integrity seals.
    - Admin-only integrity verification endpoint calculating and comparing SHA-256 checksums on cold storage records.
  - **REST API Endpoints in `src/api/reports.py`**:
    - `GET /api/reports/export/students/excel`
    - `GET /api/reports/export/finances/excel`
    - `GET /api/reports/export/attendance/excel`
    - `GET /api/reports/export/transcript/{student_id}/pdf`
    - `GET /api/reports/export/receipt/{invoice_id}/pdf`
    - `GET /api/reports/export/medical-certificate/{cert_id}/pdf`
    - `GET /api/portal/transcript/{student_id}/pdf` (portal alias)
    - `POST /api/reports/archival/cohort` (Admin only)
    - `GET /api/reports/archival/records` (Admin only)
    - `GET /api/reports/archival/records/{archive_id}` (Admin only)
    - `GET /api/reports/archival/records/{archive_id}/verify` (Admin only)
  - **Glassmorphic UI Integration**:
    - Added Excel export action buttons to `templates/reports.html`, `templates/students.html`, and `templates/finance.html`.
    - Added vector PDF download buttons to `templates/print_transcript.html`, `templates/print_receipt.html`, and `templates/portal.html`.
  - Maintained core application decoupling with `src/app.py` preserved at exactly **121 lines**.
- **Automated Testing Suite Expansion**:
  - Added comprehensive test suite `tests/test_multi_format_reports.py` covering PDF header assertions, OpenPyXL workbook structures, 404 boundaries, cohort archival workflows, and RBAC security gates.
  - Expanded test suite to **306 automated tests** passing across 28 domain test suites (100% pass rate in 11.29s).

---

## [1.6.0] - 2026-11-20

### Added
- **Identity Lifecycle, Password Self-Service & Two-Factor Authentication (Phase 14)**:
  - Engineered zero-dependency RFC 6238 Time-Based One-Time Password (`TOTPManager`, `src/core/totp.py`) engine with HMAC-SHA1 algorithm, Base32 key generation, `otpauth://` provisioning URI generation for authenticator apps, ±1 window clock-drift tolerance, and emergency single-use backup recovery codes.
  - Added schema migration `src/database/migrations/006_auth_lifecycle.sql` and updated `src/database/schema.sql` introducing `password_resets`, `user_totp`, and `user_sessions` tables with indexing and cascade constraints.
  - Implemented domain service `AuthLifecycleService` (`src/services/auth_lifecycle_service.py`):
    - Secure password reset token issuance with SHA-256 token hashing, 30-minute expiry window, silent rejection on non-existent emails (preventing user enumeration), and replay attack rejection.
    - TOTP enrollment, verification, and emergency backup recovery code consumption.
    - Active session tracking and remote device session revocation.
  - Mounted REST API router `src/api/auth_lifecycle.py` exposing:
    - `POST /api/auth/forgot-password`: Rate-limited self-service recovery request.
    - `POST /api/auth/reset-password`: Cryptographic token-authenticated password update.
    - `GET /api/auth/2fa/setup`: Generates key, QR provisioning URI, and 8 emergency backup codes.
    - `POST /api/auth/2fa/verify`: Validates 6-digit TOTP code to activate 2FA.
    - `POST /api/auth/2fa/disable`: Deactivates two-factor protection.
    - `GET /api/auth/2fa/status`: Checks active 2FA state.
    - `GET /api/auth/sessions`: Lists active device sessions.
    - `POST /api/auth/sessions/revoke`: Terminates remote device sessions.
  - Designed responsive glassmorphic recovery template `templates/reset_password.html` and added "Forgot password?" navigation flow in `templates/login.html`.
  - Added route `GET /reset-password` in `src/web/pages.py`.
  - Maintained `src/app.py` at **121 lines** (< 150 lines target strictly preserved).
- **Automated Testing Suite Expansion**:
  - Added `tests/test_auth_lifecycle_and_2fa.py` with 12 comprehensive unit and integration tests covering TOTP generation, clock drift, provisioning URIs, backup codes, token expiration, replay prevention, and remote session revocation.
  - Updated `tests/test_finance_api.py` with dynamic invoice due dates to guarantee clock-agnostic determinism.
  - Expanded test suite to **295 automated tests** passing across 27 domain test suites (100% pass rate in 4.97s).

---

## [1.5.0] - 2026-11-07

### Added
- **High-Performance SQLite FTS5 Full-Text Omnisearch (Phase 13)**:
  - Engineered virtual FTS5 indices (`fts_students`, `fts_faculty`, `fts_courses`, `fts_library_books`, `fts_announcements`) with the Porter stemmer tokenizer and Unicode 6.1 collation.
  - Added schema migration `src/database/migrations/005_fts5_search.sql` and updated `src/database/schema.sql` incorporating automatic SQLite triggers on `INSERT`, `UPDATE`, and `DELETE` for synchronous zero-latency FTS index updates.
  - Developed `SearchService` (`src/services/search_service.py`) featuring syntax-resilient query sanitization, BM25 rank scoring, highlight/snippet extraction, and role-aware visibility filters (e.g. students restricted from browsing student directories or internal circulars).
  - Mounted REST API router `src/api/search.py` providing `GET /api/search` with keyword queries (`q`), category filters (`category`), and limit controls.
  - Integrated accessible glassmorphic global Omnisearch modal in `templates/base.html` and `static/js/app.js` with `Ctrl+K` and `/` keyboard shortcuts, debounced live fetching, and instant click routing.
  - Maintained `src/app.py` at **121 lines** (< 150 lines target strictly preserved).
- **Automated Testing Suite Expansion**:
  - Added `tests/test_fts5_omnisearch.py` covering virtual table indexing, query sanitization, BM25 ranking, real-time trigger synchronization, category filters, and RBAC authentication boundaries.
  - Expanded test suite to **283 automated tests** passing across 26 domain test suites (100% pass rate in 12.44s).

---

## [1.4.0] - 2026-11-05

### Added
- **Institutional Email Dispatcher & Background Job Worker (Phase 12)**:
  - Engineered thread-safe in-process asynchronous task scheduler and worker pool `BackgroundTaskWorker` (`src/core/tasks.py`) supporting non-blocking background task enqueueing, exception isolation, and queue telemetry.
  - Implemented multi-backend email subsystem (`src/services/email_service.py`):
    - `MockEmailBackend`: In-memory thread-safe outbox buffer for unit tests and local sandboxes.
    - `ConsoleEmailBackend`: Formatted terminal stdout logger for local development.
    - `SMTPEmailBackend`: Production-grade SMTP client with STARTTLS, configurable credentials, and timeout protections.
  - Added schema migration `src/database/migrations/004_email_logs.sql` and updated `src/database/schema.sql` introducing `email_logs` table with indexes on `recipient`, `status`, and `sent_at DESC`.
  - Created responsive Jinja2 transactional HTML email templates under `templates/emails/`:
    - `fee_receipt.html`: Official electronic bursar fee receipt with itemized breakdown.
    - `leave_decision.html`: Academic leave absence petition determination notice.
    - `attendance_alert.html`: Low attendance warning sentinel (< 75% threshold).
  - Wired automated async domain event email triggers:
    - `FinanceService.record_payment`: Automatically queues electronic fee receipt to the student upon successful bursar payment recording.
    - `LeaveService.update_status`: Automatically queues decision notice to applicant upon approval or rejection.
  - Exposed REST API endpoints via `src/api/email.py`:
    - `POST /api/email/test`: Diagnostics dispatch verification (Admin-only).
    - `GET /api/email/logs`: Paginated institutional delivery audit logs with recipient filtering (Admin-only).
    - `GET /api/system/tasks`: Live background worker pool queue telemetry and load metrics.
  - Registered worker pool graceful shutdown in `src/app.py:lifespan` (`shutdown_task_worker_pool(wait=False)`), maintaining `src/app.py` at **121 lines** (well below 150 lines limit).
- **Automated Testing Suite Expansion**:
  - Added `tests/test_background_tasks_and_email.py` containing 15 comprehensive unit and integration tests.
  - Expanded test suite to **271 automated tests** across 25 domain suites (100% pass rate in 8.68s).

---

## [1.3.0] - 2026-11-04

### Added
- **Secure Document & Media Storage Subsystem (Phase 11)**:
  - Engineered `StorageManager` (`src/core/storage.py`) providing binary magic-byte inspection (PNG, JPEG, GIF, WebP, PDF, DOCX), fail-closed forbidden extension gating, and path traversal guards.
  - Added isolated file persistence under `data/uploads/` using randomized opaque UUID filenames (`doc_<uuid>.<ext>`).
  - Added schema migration `src/database/migrations/003_document_storage.sql` establishing `uploaded_documents` table with indexes on `file_id`, `category`, and `created_at`.
  - Built domain service `StorageService` (`src/services/storage_service.py`) and Pydantic schemas (`src/models/storage.py`) managing document lifecycle.
  - Mounted REST API router `src/api/storage.py` providing `POST /api/storage/upload`, `GET /api/storage/files/{file_id}`, `GET /api/storage/documents`, and `DELETE /api/storage/files/{file_id}` with role-aware privacy boundaries and audit logging.
  - Consolidated router registration in `src/api/__init__.py:ALL_API_ROUTERS`, streamlining `src/app.py` from 146 to **119 lines** (< 150 lines target strictly preserved).
- **Automated Testing Suite Expansion**:
  - Added `tests/test_storage_api.py` with 10 comprehensive tests covering binary magic bytes, disguised executables, forbidden extensions, 413 payload limits, path traversal rejection, and RBAC document deletion.
  - Expanded test suite to **256 automated unit and integration tests** passing cleanly across 24 domain test suites (100% pass rate in 9.05s).

---

## [1.2.0] - 2026-11-02

### Added
- **Architectural Refactoring & Core App Decoupling**:
  - Decoupled `src/app.py` from 312 lines down to 146 lines (< 150 lines target achieved).
  - Extracted OpenAPI tag documentation definitions into dedicated module `src/core/openapi.py`.
  - Extracted glassmorphic HTML error page renderers and structured JSON exception handlers into `src/core/exceptions.py`.
- **Database Schema Migration & Version Tracking Engine**:
  - Implemented `MigrationManager` (`src/database/migration_manager.py`) tracking versions, checksums, and execution latencies in `schema_migrations`.
  - Added initial migrations `001_initial_schema.sql` and `002_notifications.sql`.
  - Added REST API endpoints `GET /api/system/migrations` and `POST /api/system/migrate` with audit logging.
  - Added `make migrate` and `make migration-status` developer targets.
- **SQLite WAL Optimization & Administrative Settings Diagnostics**:
  - Added `POST /api/system/optimize` endpoint performing `PRAGMA wal_checkpoint(TRUNCATE)` and query planner optimization.
  - Enhanced settings UI (`templates/settings.html`) with interactive Schema Migration status panel and 30-event Institutional Audit Trail tab.
- **Institutional Notifications & Alert Dispatch Engine**:
  - Built real-time notification subsystem (`src/models/notification.py`, `src/services/notification_service.py`, `src/api/notifications.py`).
  - Added target audience filtering (`ALL`, `STUDENT`, `FACULTY`, `ADMIN`), priority levels (`LOW`, `NORMAL`, `HIGH`, `URGENT`), and unread indicator counters.
  - Added automated sentinel dispatch triggers for low attendance warnings (< 75%) and bursar fee overdue notices.
  - Designed responsive glassmorphic alert feed page (`templates/notifications.html`) with 1-click "Mark All as Read" and broadcast modal.
  - Added real-time notification alert link to top navigation bar and global sidebar in `templates/base.html`.
- **Executive Dashboard Visual Analytics**:
  - Enhanced overview dashboard (`templates/dashboard.html`) with zero-dependency responsive SVG visual analytics cards:
    - Fiscal Recovery & Cash Flow Progress Donut Chart.
    - Institutional Attendance Health Gauge Sentinel.
    - Quick-access Alerts Feed button.
- **Automated Testing Suite Expansion**:
  - **246 automated unit and integration tests** passing cleanly across 23 domain test suites (100% pass rate).
  - Expanded test suite with comprehensive migration execution, notification lifecycle, WAL checkpoint optimization, and settings diagnostic tabs.

---

## [1.1.0] - 2026-10-30

### Added
- **Production Readiness & Atomic Database State Restoration**:
  - Point-in-time database snapshot restoration service (`SystemService.restore_backup`) and REST API (`POST /api/system/restore`).
  - Pre-restore snapshot integrity verification (`PRAGMA integrity_check`) and path traversal sanitization.
  - Automatic `TTLCache` invalidation on state restore to prevent stale query cache reads.
  - Admin RBAC enforcement and immutable audit logging for database restoration actions (`SYSTEM_RESTORE`).
- **Production Load Testing & Concurrency Benchmark Suite**:
  - High-concurrency benchmark script (`scripts/load_test.py`) simulating 15+ worker threads.
  - Telemetry reporting for p50, p90, p95, p99 latencies, throughput (86.7+ req/s), and HTTP status distributions.
  - Zero database lock contention under SQLite WAL mode and reusable connection pooling.
- **Developer Tooling & Makefile Expansion**:
  - `make restore FILE=...` target for one-command point-in-time database recovery.
  - `make load-test` target for running concurrent load benchmarks.
- **Automated Testing Suite Expansion**:
  - **238 automated unit and integration tests** passing cleanly across 22 test suites (100% pass rate in 8.8s).
  - Production readiness tests for concurrent user load, environment configuration audits, and backup-restore cycles.

---

## [1.0.0] - 2026-10-29

### Added
- **Core Architecture & High Performance Data Layer**:
  - Thread-safe SQLite connection pool with reusable queue and transaction rollback protection.
  - In-memory `TTLCache` engine with key-based and pattern-based invalidation for cached lookups.
  - SQLite WAL (Write-Ahead Logging) mode and foreign key constraints.
  - 16+ composite database performance indexes across hot query paths.
  - Server-side pagination (`page`, `limit`) across student rosters, course catalog, and bursar invoices.
- **18 Comprehensive Institutional Domains**:
  - Scholar Admissions & Sequential Registration (`IMS-YYYY-DEPT-XXXX`).
  - Faculty Instructor Directory & Academic Department Organization.
  - Course Catalog, Multi-Semester Curriculum & Capacity Gating.
  - Session Attendance Register (Present, Absent, Late, Excused).
  - Examination Scheduling, Grade Submission & GPA Evaluation ($A^+, A, B, C, D, F$).
  - Departmental Fee Structures, Bursar Invoicing (`INV-YYYY-XXXX`), and Receipt Hash Ledger.
  - Campus Bulletins & Announcements with Priority Audiences (`/announcements`).
  - Lecture Timetable Scheduling with Collision Avoidance (`/timetable`).
  - Dean Leave Management Petition Workflow (`/leaves`).
  - Campus Library & ISBN Monograph Circulation (`/library`).
  - Hostel & Residential Hall Housing Management (`/hostel`).
  - Corporate Placements & Career Recruitment Drives (`/placements`).
  - Campus Transport Transit Fleet Logistics (`/transport`).
  - Scholarships, Endowment Grants & Financial Aid (`/scholarships`).
  - Alumni Mentorship & Professional Networking (`/alumni`).
  - Campus Events, Technical Symposiums & Hackathons (`/events`).
  - Scientific Lab Instruments & Asset Inventory Circulation (`/inventory`).
  - Campus Health Center, Electronic Encounters & Dispensary Infirmary (`/health-center`).
- **User Portals & Institutional Telemetry**:
  - Student Self-Service Portal & Dossier (`/portal`).
  - Faculty Instructor Workbench (`/faculty-portal`).
  - Institutional Reports & Real-Time `< 75%` Attendance Risk Sentinel (`/reports`).
  - Streaming CSV Data Export Engine (`/api/reports/export/*`).
  - System Telemetry, Health Probes & Atomic Hot Database Backups (`/settings`).
  - Print-ready official academic transcripts and official bursar fee receipts.
- **Security & Reliability Hardening**:
  - Session-based authentication with role-based access control (Admin, Faculty, Student).
  - Rate limiting with thread-safe sliding-window brute-force login lockout (5 attempts / 5 min).
  - OWASP Security Headers middleware (CSP, X-Frame-Options, X-Content-Type-Options).
  - Request body payload size limit middleware (10MB limit with HTTP 413).
  - Admin-only authorization for destructive operations with immutable audit trail logging.
  - Explicit Jinja2 auto-escaping to mitigate XSS.
- **Comprehensive Automated Testing**:
  - **231 automated unit and integration tests** passing cleanly across 21 test suites.
  - Service-layer isolation tests, concurrency safety validation, and boundary verification.
- **Developer Tooling & Experience**:
  - Developer `Makefile` with targets for testing, linting, formatting, seeding, and backups.
  - Git `.pre-commit-config.yaml` for Ruff linting and formatting.
  - Comprehensive `.env.example` with documented environment configurations.
  - Detailed `CONTRIBUTING.md` developer guide.
