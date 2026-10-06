"""Tests for Attendance Tracking and Examination Grading APIs."""


def test_mark_attendance_batch(client):
    """Verify batch attendance marking."""
    # Ensure course and student exist
    c_res = client.post(
        "/api/courses",
        json={
            "code": "ATT101",
            "title": "Attendance Test Unit",
            "department_id": 1,
            "credits": 3,
            "semester": 1,
            "capacity": 40,
        },
    )
    course_id = c_res.json()["id"]

    s_res = client.post(
        "/api/students",
        json={
            "first_name": "Kavita",
            "last_name": "Patel",
            "email": "kavita.patel@example.edu",
            "department_id": 1,
            "current_semester": 1,
        },
    )
    student_id = s_res.json()["id"]

    # Mark attendance
    batch_payload = {
        "course_id": course_id,
        "attendance_date": "2026-10-06",
        "records": [
            {"student_id": student_id, "status": "PRESENT", "remarks": "On time"},
        ],
    }
    res = client.post("/api/academics/attendance/mark", json=batch_payload)
    assert res.status_code == 201
    assert res.json()["records_marked"] == 1


def test_attendance_upsert_on_same_date(client):
    """Verify updating attendance status on duplicate date."""
    c_res = client.get("/api/courses?search=ATT101")
    course_id = c_res.json()[0]["id"]

    s_res = client.get("/api/students?search=Kavita")
    student_id = s_res.json()[0]["id"]

    # Change to ABSENT on same date
    update_payload = {
        "course_id": course_id,
        "attendance_date": "2026-10-06",
        "records": [
            {"student_id": student_id, "status": "ABSENT", "remarks": "Excused sick"},
        ],
    }
    res = client.post("/api/academics/attendance/mark", json=update_payload)
    assert res.status_code == 201

    # Verify status changed
    rec_res = client.get(
        f"/api/academics/attendance?course_id={course_id}&attendance_date=2026-10-06"
    )
    assert rec_res.status_code == 200
    records = rec_res.json()
    assert len(records) == 1
    assert records[0]["status"] == "ABSENT"


def test_student_attendance_summary(client):
    """Verify attendance summary and percentage computation."""
    s_res = client.get("/api/students?search=Kavita")
    student_id = s_res.json()[0]["id"]

    res = client.get(f"/api/academics/attendance/student/{student_id}/summary")
    assert res.status_code == 200
    data = res.json()
    assert data["student_id"] == student_id
    assert data["total_classes"] >= 1
    assert "attendance_percentage" in data
    assert "is_short_attendance" in data


def test_schedule_examination(client):
    """Verify scheduling an assessment."""
    c_res = client.get("/api/courses?search=ATT101")
    course_id = c_res.json()[0]["id"]

    payload = {
        "course_id": course_id,
        "title": "ATT101 Midterm Exam",
        "exam_type": "MIDTERM",
        "exam_date": "2026-10-20",
        "max_marks": 100.0,
        "passing_marks": 40.0,
        "weightage_percent": 30.0,
    }
    res = client.post("/api/academics/exams", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "ATT101 Midterm Exam"
    assert data["max_marks"] == 100.0
    assert data["course_code"] == "ATT101"


def test_submit_exam_grades_batch(client):
    """Verify batch grade evaluation and letter grade assignment."""
    exams = client.get("/api/academics/exams").json()
    exam = [e for e in exams if e["title"] == "ATT101 Midterm Exam"][0]
    exam_id = exam["id"]

    s_res = client.get("/api/students?search=Kavita")
    student_id = s_res.json()[0]["id"]

    grades_payload = {
        "grades": [
            {"student_id": student_id, "marks_obtained": 92.5, "remarks": "Outstanding work"},
        ]
    }
    res = client.post(f"/api/academics/exams/{exam_id}/grades", json=grades_payload)
    assert res.status_code == 200
    assert res.json()["graded_count"] == 1


def test_grade_exceeds_max_marks_rejected(client):
    """Verify rejecting marks exceeding maximum marks."""
    exams = client.get("/api/academics/exams").json()
    exam = [e for e in exams if e["title"] == "ATT101 Midterm Exam"][0]
    exam_id = exam["id"]

    s_res = client.get("/api/students?search=Kavita")
    student_id = s_res.json()[0]["id"]

    invalid_grades = {
        "grades": [
            {"student_id": student_id, "marks_obtained": 105.0},
        ]
    }
    res = client.post(f"/api/academics/exams/{exam_id}/grades", json=invalid_grades)
    assert res.status_code == 400
    assert "cannot exceed maximum marks" in res.json()["detail"]


def test_exam_results_dossier_and_statistics(client):
    """Verify performance metrics and letter grade resolution."""
    exams = client.get("/api/academics/exams").json()
    exam = [e for e in exams if e["title"] == "ATT101 Midterm Exam"][0]
    exam_id = exam["id"]

    res = client.get(f"/api/academics/exams/{exam_id}/results")
    assert res.status_code == 200
    data = res.json()
    stats = data["statistics"]
    assert stats["total_candidates"] == 1
    assert stats["average_marks"] == 92.5
    assert stats["highest_marks"] == 92.5
    assert stats["pass_rate"] == 100.0

    candidate = data["roster"][0]
    assert candidate["grade_letter"] == "A+"
    assert candidate["marks_obtained"] == 92.5


def test_view_academics_html_page(client):
    """Verify HTML rendering of academics portal."""
    response = client.get("/academics")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "Attendance & Academic Examinations" in html
    assert "Daily Attendance Register" in html
    assert "Examination Schedule" in html
