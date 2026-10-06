"""Tests for Faculty & Course Management APIs and Views."""


def test_create_faculty_member(client):
    """Verify registering a faculty member."""
    payload = {
        "first_name": "Ada",
        "last_name": "Lovelace",
        "email": "ada.lovelace@example.edu",
        "phone": "+1 555-0100",
        "department_id": 1,
        "designation": "Professor & Chair",
        "qualification": "Ph.D. in Computer Science",
        "status": "ACTIVE",
    }
    res = client.post("/api/faculty", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["first_name"] == "Ada"
    assert data["faculty_id"].startswith("FAC-")
    assert data["department_name"] == "Computer Science & Engineering"


def test_faculty_duplicate_email(client):
    """Verify duplicate email rejection for faculty."""
    payload = {
        "first_name": "Ada",
        "last_name": "Duplicate",
        "email": "ada.lovelace@example.edu",
        "department_id": 1,
    }
    res = client.post("/api/faculty", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]


def test_list_faculty_filter(client):
    """Verify listing faculty with department filter."""
    res = client.get("/api/faculty?department_id=1")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert any(f["email"] == "ada.lovelace@example.edu" for f in data)


def test_create_course(client):
    """Verify adding a curriculum course unit."""
    # First get Ada's ID
    fac_res = client.get("/api/faculty?search=Ada")
    instructor_id = fac_res.json()[0]["id"]

    payload = {
        "code": "CS101",
        "title": "Introduction to Computer Science & Python",
        "department_id": 1,
        "credits": 4,
        "semester": 1,
        "capacity": 60,
        "syllabus_summary": "Algorithms, data structures, and functional programming",
        "instructor_id": instructor_id,
    }
    res = client.post("/api/courses", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["code"] == "CS101"
    assert data["credits"] == 4
    assert data["instructor_name"] == "Ada Lovelace"
    assert data["enrolled_count"] == 0


def test_course_duplicate_code(client):
    """Verify course code uniqueness check."""
    payload = {
        "code": "CS101",
        "title": "Duplicate CS101",
        "department_id": 1,
        "credits": 3,
        "semester": 1,
        "capacity": 50,
    }
    res = client.post("/api/courses", json=payload)
    assert res.status_code == 400
    assert "already in use" in res.json()["detail"]


def test_assign_instructor_to_course(client):
    """Verify assigning or changing course instructor."""
    # Create another course unassigned
    payload = {
        "code": "CS102",
        "title": "Discrete Mathematics",
        "department_id": 1,
        "credits": 3,
        "semester": 1,
        "capacity": 45,
    }
    create_res = client.post("/api/courses", json=payload)
    assert create_res.status_code == 201
    course_id = create_res.json()["id"]

    fac_res = client.get("/api/faculty?search=Ada")
    instructor_id = fac_res.json()[0]["id"]

    assign_res = client.post(
        f"/api/courses/{course_id}/assign-instructor?instructor_id={instructor_id}"
    )
    assert assign_res.status_code == 200
    assert assign_res.json()["instructor_name"] == "Ada Lovelace"


def test_enroll_student_in_course(client):
    """Verify enrolling student into course."""
    # Ensure student exists
    stu_res = client.post(
        "/api/students",
        json={
            "first_name": "Grace",
            "last_name": "Hopper",
            "email": "grace.hopper@example.edu",
            "department_id": 1,
            "current_semester": 1,
            "status": "ENROLLED",
        },
    )
    student_id = stu_res.json()["id"]

    # Get CS101 course
    course_res = client.get("/api/courses?search=CS101")
    course_id = course_res.json()[0]["id"]

    enroll_payload = {
        "student_id": student_id,
        "course_id": course_id,
        "academic_year": "2026-2027",
        "semester": 1,
    }
    en_res = client.post("/api/courses/enroll", json=enroll_payload)
    assert en_res.status_code == 201
    en_data = en_res.json()
    assert en_data["student_name"] == "Grace Hopper"
    assert en_data["course_code"] == "CS101"

    # Verify enrolled_count increased to 1
    updated_course = client.get(f"/api/courses/{course_id}").json()
    assert updated_course["enrolled_count"] == 1


def test_duplicate_enrollment_prevention(client):
    """Verify preventing duplicate enrollment in the same course and semester."""
    stu_res = client.get("/api/students?search=Grace")
    student_id = stu_res.json()[0]["id"]

    course_res = client.get("/api/courses?search=CS101")
    course_id = course_res.json()[0]["id"]

    enroll_payload = {
        "student_id": student_id,
        "course_id": course_id,
        "academic_year": "2026-2027",
        "semester": 1,
    }
    dup_res = client.post("/api/courses/enroll", json=enroll_payload)
    assert dup_res.status_code == 400
    assert "already enrolled" in dup_res.json()["detail"]


def test_capacity_limit_enforcement(client):
    """Verify capacity constraint prevents over-enrollment."""
    # Create course with capacity = 1
    c_res = client.post(
        "/api/courses",
        json={
            "code": "CAP101",
            "title": "Exclusive Seminar",
            "department_id": 1,
            "credits": 1,
            "semester": 1,
            "capacity": 1,
        },
    )
    course_id = c_res.json()["id"]

    # Enroll Grace
    stu_res = client.get("/api/students?search=Grace")
    grace_id = stu_res.json()[0]["id"]
    client.post(
        "/api/courses/enroll",
        json={
            "student_id": grace_id,
            "course_id": course_id,
            "academic_year": "2026-2027",
            "semester": 1,
        },
    )

    # Try enrolling second student
    s2_res = client.post(
        "/api/students",
        json={
            "first_name": "Nikola",
            "last_name": "Tesla",
            "email": "nikola.tesla@example.edu",
            "department_id": 1,
            "current_semester": 1,
        },
    )
    s2_id = s2_res.json()["id"]

    overflow_res = client.post(
        "/api/courses/enroll",
        json={
            "student_id": s2_id,
            "course_id": course_id,
            "academic_year": "2026-2027",
            "semester": 1,
        },
    )
    assert overflow_res.status_code == 400
    assert "maximum capacity" in overflow_res.json()["detail"]


def test_list_enrolled_students(client):
    """Verify fetching roster of enrolled students."""
    course_res = client.get("/api/courses?search=CS101")
    course_id = course_res.json()[0]["id"]

    roster_res = client.get(f"/api/courses/{course_id}/students")
    assert roster_res.status_code == 200
    roster = roster_res.json()
    assert len(roster) >= 1
    assert any(s["first_name"] == "Grace" for s in roster)


def test_view_courses_html_page(client):
    """Verify HTML rendering of courses and faculty portal."""
    response = client.get("/courses")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "Faculty & Course Curriculum" in html
    assert "CS101" in html
    assert "Ada Lovelace" in html
