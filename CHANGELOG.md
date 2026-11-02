# Changelog

All notable changes to the **Institute Management System (IMS Enterprise)** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
  - **244 automated unit and integration tests** passing cleanly across 23 domain test suites (100% pass rate in 7.9s).
  - Expanded test suite with comprehensive migration execution, notification lifecycle, and alert trigger test cases.

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
