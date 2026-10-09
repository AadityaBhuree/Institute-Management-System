# 🏛️ Institute Management System (IMS Enterprise)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57.svg?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Tests](https://img.shields.io/badge/Pytest-75%2F75%20Passing-success.svg)](tests/)
[![CI](https://github.com/AadityaBhuree/Institute-Management-System/actions/workflows/ci.yml/badge.svg)](https://github.com/AadityaBhuree/Institute-Management-System/actions/workflows/ci.yml)
[![Docker](https://img.shields.io/badge/Docker-Multi--Stage-2496ED.svg?logo=docker&logoColor=white)](Dockerfile)
[![Code Style](https://img.shields.io/badge/Linter-Ruff%20Clean-black.svg)](pyproject.toml)
[![Architecture](https://img.shields.io/badge/Architecture-Clean%20%2F%20Layered-indigo.svg)](src/)

A modern, high-performance, and modular educational administration platform built with **FastAPI**, **SQLite** (WAL mode), and a responsive **Glassmorphism Web Dashboard**. Engineered for academic institutions, colleges, and university divisions to automate admissions, course scheduling, attendance registries, academic grading, bursar financial audits, lecture timetables, and campus bulletins.

---

## 📌 Executive Architecture & Highlights

* **Admissions & Scholar Registry:** Sequential institutional enrollment code generation (`IMS-YYYY-DEPT-XXXX`), full scholar profile management, department filtering, and real-time status transitions.
* **Faculty Directory & Curriculum:** Faculty instructor directory, multi-semester course catalog, credit tracking, and automated capacity-enforced student course enrollments.
* **Attendance & Examination Hub:** Daily session attendance registers (Present, Absent, Late, Excused), examination scheduling (Midterms, Finals, Quizzes), batch grade submission, and automated grading letter evaluation ($A^+, A, B, C, D, F$).
* **Bursar Invoicing & Financial Audit:** Standardized departmental fee schedules, student invoice issuance (`INV-YYYY-XXXX`), partial and full payment collection, unique receipt numbering (`REC-YYYY-XXXX`), overdue calculation, financial ledger audit, and print-ready official fee receipts.
* **Campus Bulletins & Announcements:** Institutional broadcast engine with priority tags (`HIGH`, `NORMAL`, `LOW`), target audience filtering (`ALL`, `STUDENTS`, `FACULTY`), and circular lifecycle management (`/announcements`).
* **Lecture Timetable & Conflict Sentinel:** Weekly scheduling matrix with automated classroom double-booking collision prevention and instructor schedule overlap detection (`/timetable`).
* **Institutional Leave Management:** Absence petitions, medical leaves, duty slips, and Dean review decision workflows with status telemetry (`/leaves`).
* **Student & Faculty Portals:** Scholar self-service academic dossier (`/portal`), faculty teaching workbench (`/faculty-portal`), institutional reports & `< 75%` attendance risk sentinel (`/reports`), and official printable transcripts.
* **Sleek Enterprise UX:** Vanilla CSS glassmorphic theme (`#090d16` & `#0f172a`), interactive modals, responsive sidebar, toast notifications, and KPI overview cards.

---

## 🏗️ System Architecture & Entity Relationships

```mermaid
erDiagram
    DEPARTMENTS ||--o{ FACULTY : employs
    DEPARTMENTS ||--o{ COURSES : offers
    DEPARTMENTS ||--o{ STUDENTS : enrolls
    DEPARTMENTS ||--o{ FEE_STRUCTURES : defines
    FACULTY ||--o{ COURSES : instructs
    STUDENTS ||--o{ COURSE_ENROLLMENTS : registers
    COURSES ||--o{ COURSE_ENROLLMENTS : includes
    COURSES ||--o{ TIMETABLE_SLOTS : schedules
    STUDENTS ||--o{ ATTENDANCE_RECORDS : logs
    COURSES ||--o{ ATTENDANCE_RECORDS : holds
    COURSES ||--o{ EXAMINATIONS : schedules
    EXAMINATIONS ||--o{ EXAM_RESULTS : evaluates
    STUDENTS ||--o{ EXAM_RESULTS : achieves
    STUDENTS ||--o{ FEE_INVOICES : billed_to
    FEE_INVOICES ||--o{ FEE_PAYMENTS : settles
    STUDENTS ||--o{ LEAVE_REQUESTS : requests
```

---

## 📁 Repository Directory Structure

```
Institute Management System/
├── data/
│   ├── backups/                    # Hot online SQLite point-in-time database backups
│   └── ims.db                      # SQLite database in WAL mode with foreign keys
├── scripts/
│   └── seed_demo_data.py           # Idempotent realistic demonstration dataset seeder
├── src/
│   ├── api/                        # Modular FastAPI REST API route handlers
│   │   ├── academics.py            # Attendance and examination endpoints
│   │   ├── announcements.py        # Campus bulletin and announcements endpoints
│   │   ├── courses.py              # Course catalog and enrollment endpoints
│   │   ├── faculty.py              # Faculty directory endpoints
│   │   ├── finance.py              # Invoicing, receipts, and audit endpoints
│   │   ├── leaves.py               # Leave application and approval endpoints
│   │   ├── reports.py              # Institutional analytics and telemetry endpoints
│   │   ├── students.py             # Admissions and scholar endpoints
│   │   └── timetable.py            # Lecture timetable and scheduling endpoints
│   ├── core/
│   │   └── config.py               # Application configuration and path tokens
│   ├── database/
│   │   ├── connection.py           # SQLite connection pool and atomic transaction contexts
│   │   ├── init_db.py              # Schema deployment and seed verification
│   │   └── schema.sql              # Relational DDL schema with 14 tables & 19 indexes
│   ├── models/                     # Strongly-typed Pydantic schemas (v2)
│   │   ├── academics.py            # Attendance and exam request/response schemas
│   │   ├── announcement.py         # Campus bulletin schemas
│   │   ├── course.py               # Course and enrollment schemas
│   │   ├── department.py           # Department schemas
│   │   ├── faculty.py              # Faculty schemas
│   │   ├── finance.py              # Fee structure, invoice, and payment schemas
│   │   ├── leave.py                # Leave petition and review schemas
│   │   ├── student.py              # Admissions and scholar registry schemas
│   │   └── timetable.py            # Timetable slot schemas
│   ├── services/                   # Business logic and database operations
│   │   ├── academics_service.py    # Attendance and exam evaluation logic
│   │   ├── announcement_service.py # Bulletin CRUD and priority query logic
│   │   ├── course_service.py       # Course scheduling and capacity enforcement
│   │   ├── dashboard_service.py    # Executive KPI metric aggregations
│   │   ├── department_service.py   # Department operations
│   │   ├── faculty_service.py      # Faculty management & teaching workbench
│   │   ├── finance_service.py      # Invoicing, receipts, and ledger audit
│   │   ├── leave_service.py        # Absence petitions and approval workflows
│   │   ├── reports_service.py      # Institutional telemetry and risk sentinels
│   │   ├── student_service.py      # Student registry and admission routines
│   │   ├── system_service.py       # Telemetry and hot SQLite online backup engine
│   │   └── timetable_service.py    # Timetable matrix and collision avoidance logic
│   └── app.py                      # FastAPI application, static mounting, and page routes
├── static/
│   ├── css/
│   │   └── style.css               # Design system: Glassmorphism, animations, toast rules
│   └── js/
│       └── app.js                  # Frontend utilities, modal handlers, and toast notifications
├── templates/                      # Jinja2 SSR Templates
│   ├── academics.html              # Attendance register and exam grading hub
│   ├── announcements.html          # Campus bulletin board and notice broadcast hub
│   ├── base.html                   # Global glassmorphic sidebar layout
│   ├── courses.html                # Course catalog and faculty roster portal
│   ├── dashboard.html              # Executive overview dashboard
│   ├── faculty_portal.html         # Faculty instructor workbench
│   ├── finance.html                # Invoicing, payment collection, and audit ledger
│   ├── leaves.html                 # Leave management and absence approval portal
│   ├── portal.html                 # Student self-service scholar portal
│   ├── print_receipt.html          # Printable official fee receipt with seal
│   ├── print_transcript.html       # Printable academic transcript dossier
│   ├── reports.html                # Institutional analytics and attendance sentinel
│   ├── settings.html               # System telemetry and hot online database backups
│   ├── students.html               # Admissions and student registry directory
│   └── timetable.html              # Weekly academic lecture timetable matrix
├── tests/                          # Automated Pytest validation suite (75 tests)
│   ├── conftest.py                 # Isolated test database runner
│   ├── test_academics_api.py       # Attendance and examination API test cases
│   ├── test_announcements_api.py   # Bulletin board API and web test cases
│   ├── test_core_and_dashboard.py  # Health check, settings, and backup test cases
│   ├── test_courses_and_faculty.py # Course catalog and faculty test cases
│   ├── test_finance_api.py         # Invoices, receipts, and printable receipt tests
│   ├── test_leaves_api.py          # Leave application and approval test cases
│   ├── test_students_api.py        # Admissions, scholar portal, and transcript tests
│   └── test_timetable_api.py       # Timetable scheduling and collision test cases
├── Dockerfile                      # Multi-stage production container
├── docker-compose.yml              # Persistent volume container deployment
├── render.yaml                     # Infrastructure-as-code cloud blueprint
├── pyproject.toml                  # Project metadata, Ruff rules, and Pytest configuration
├── requirements.txt                # Production dependencies
└── README.md                       # Architectural documentation
```

---

## 🔌 Complete RESTful API Reference

### 🎓 Admissions & Students
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/students` | Enroll a new student and issue sequential enrollment ID |
| `GET` | `/api/students` | List students with department, semester, and text filters |
| `GET` | `/api/students/{id}` | Retrieve individual student demographic profile |
| `PUT` | `/api/students/{id}` | Update scholar contact, address, or academic semester |
| `DELETE` | `/api/students/{id}` | Soft-delete / withdraw student registration |
| `GET` | `/api/students/stats/summary` | Academic enrollment metrics and semester breakdown |

### 📚 Faculty & Course Catalog
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/faculty` | Add faculty member with unique institutional faculty ID |
| `GET` | `/api/faculty` | List faculty roster filtered by department or status |
| `GET` | `/api/faculty/{id}` | Retrieve faculty instructor dossier |
| `POST` | `/api/courses` | Create an academic course with credits and seat capacity |
| `GET` | `/api/courses` | List course catalog with active enrollment counts |
| `POST` | `/api/courses/enroll` | Enroll student into course with capacity checking |
| `GET` | `/api/courses/{id}/students`| List all enrolled students for a specific course |

### 📝 Attendance & Examinations
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/academics/attendance/mark` | Batch mark daily session attendance (PRESENT/ABSENT/LATE) |
| `GET` | `/api/academics/attendance` | Retrieve session attendance roster for a course & date |
| `GET` | `/api/academics/attendance/student/{id}/summary` | Scholar attendance percentage and low-attendance alert |
| `POST` | `/api/academics/exams` | Schedule examination with weightage and passing marks |
| `GET` | `/api/academics/exams` | List scheduled examinations and grading statuses |
| `POST` | `/api/academics/exams/{id}/grades` | Batch submit student exam scores and calculate letter grades |
| `GET` | `/api/academics/exams/{id}/results` | Retrieve graded evaluation dossier and statistics |

### 💳 Fee Invoicing & Financial Audit
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/finance/fee-structures` | Configure standardized departmental semester fee schedule |
| `GET` | `/api/finance/fee-structures` | List departmental fee schedules |
| `POST` | `/api/finance/invoices` | Issue student fee invoice with unique number (`INV-2026-XXXX`) |
| `GET` | `/api/finance/invoices` | List fee invoices filtered by status, department, and search |
| `GET` | `/api/finance/invoices/{id}` | Get detailed invoice with historical payment receipts |
| `POST` | `/api/finance/payments` | Record fee payment, update balance, and issue receipt (`REC-XXXX`)|
| `GET` | `/api/finance/payments` | Query the real-time bursar payment audit ledger |
| `GET` | `/api/finance/summary` | Executive financial summary (billed, collected, collection rate) |

### 📢 Campus Notice Board & Announcements
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/announcements` | Post institutional notice with priority tags & audience |
| `GET` | `/api/announcements` | Query campus notices filtered by audience, category, status |
| `GET` | `/api/announcements/{id}` | Retrieve individual announcement notice |
| `PUT` | `/api/announcements/{id}/toggle-active` | Archive or publish bulletin notice |
| `DELETE` | `/api/announcements/{id}` | Remove announcement from bulletin board |

### 🗓️ Lecture Timetable & Scheduling
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/timetable` | Schedule lecture slot with room & instructor collision avoidance |
| `GET` | `/api/timetable` | Query scheduled lecture slots with room & course metadata |
| `GET` | `/api/timetable/matrix` | Weekly schedule matrix organized Monday through Saturday |
| `GET` | `/api/timetable/{id}` | Retrieve individual timetable slot |
| `DELETE` | `/api/timetable/{id}` | Remove lecture slot from timetable |

### 📋 Leave Management & Absence Petitions
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/leaves` | Submit student or faculty absence/leave petition |
| `GET` | `/api/leaves` | List leave requests filtered by role, status, applicant ID |
| `GET` | `/api/leaves/stats/summary` | Aggregate leave metrics (Pending, Approved, Rejected) |
| `GET` | `/api/leaves/{id}` | Retrieve individual leave petition dossier |
| `PUT` | `/api/leaves/{id}/status` | Review and approve/reject leave petition with remarks |

---

## 🚀 Quickstart & Installation

### 1. Prerequisites
* Python 3.10+ installed

### 2. Setup Virtual Environment
```bash
python -m venv .venv

# On Windows PowerShell:
.venv\Scripts\Activate.ps1

# On macOS/Linux:
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Seed Realistic Demonstration Data
```bash
python scripts/seed_demo_data.py
```

### 5. Launch Application Server (Local)
```bash
python -m uvicorn src.app:app --reload --port 8000
```

### 6. Run with Docker / Container (Production)
```bash
# 1-Click Launch with Docker Compose (mounts ./data with persistent SQLite WAL storage)
docker compose up -d

# Or build and run standalone container
docker build -t ims-enterprise .
docker run -d -p 8000:8000 -v $(pwd)/data:/app/data --name ims_app ims-enterprise
```

Open **[http://localhost:8000](http://localhost:8000)** in your browser:
* **Overview Dashboard:** `http://localhost:8000/`
* **Student Registry:** `http://localhost:8000/students`
* **Scholar Self-Service Portal:** `http://localhost:8000/portal`
* **Faculty Instructor Workbench:** `http://localhost:8000/faculty-portal`
* **Courses & Faculty Catalog:** `http://localhost:8000/courses`
* **Attendance & Exams Hub:** `http://localhost:8000/academics`
* **Lecture Timetable Matrix:** `http://localhost:8000/timetable`
* **Campus Bulletins & Notices:** `http://localhost:8000/announcements`
* **Leave Management Portal:** `http://localhost:8000/leaves`
* **Fee Invoicing & Bursar Audit:** `http://localhost:8000/finance`
* **Institutional Reports & Sentinel:** `http://localhost:8000/reports`
* **System Settings & Hot Backup:** `http://localhost:8000/settings`
* **Health Endpoint:** `http://localhost:8000/api/health`
* **Interactive OpenAPI Docs:** `http://localhost:8000/docs`

---

## 🧪 Testing & Verification

The test suite runs with isolated SQLite databases in temporary environments via pytest fixtures:

```bash
# Run all 75 automated unit and integration tests
pytest tests/ -v

# Run Ruff linter to confirm clean code hygiene
ruff check src/ tests/ scripts/
```

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
