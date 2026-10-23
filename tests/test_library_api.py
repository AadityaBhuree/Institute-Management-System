"""Unit and integration test suite for Campus Library & Resource Circulation."""

from fastapi.testclient import TestClient


def test_create_library_book(client: TestClient):
    payload = {
        "isbn": "978-0134685991",
        "title": "Effective Java",
        "author": "Joshua Bloch",
        "category": "COMPUTER_SCIENCE",
        "total_copies": 4,
        "shelf_location": "Stack CS-2",
        "publisher": "Addison-Wesley",
        "edition": "3rd Ed",
        "publication_year": 2018,
    }
    res = client.post("/api/library/books", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["id"] is not None
    assert data["title"] == "Effective Java"
    assert data["available_copies"] == 4
    assert data["isbn"] == "978-0134685991"


def test_duplicate_isbn_rejection(client: TestClient):
    payload = {
        "isbn": "978-0134685991",  # Same ISBN as above
        "title": "Duplicate Effective Java",
        "author": "Joshua Bloch",
        "category": "COMPUTER_SCIENCE",
        "total_copies": 2,
    }
    res = client.post("/api/library/books", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]


def test_list_books_and_filters(client: TestClient):
    # Add another book under MATHEMATICS
    client.post(
        "/api/library/books",
        json={
            "isbn": "978-0198534969",
            "title": "Discrete Mathematics and its Applications",
            "author": "Kenneth H. Rosen",
            "category": "MATHEMATICS",
            "total_copies": 2,
            "shelf_location": "Stack MATH-1",
        },
    )

    # Filter by category
    res_math = client.get("/api/library/books?category=MATHEMATICS")
    assert res_math.status_code == 200
    math_books = res_math.json()
    assert len(math_books) >= 1
    assert all(b["category"] == "MATHEMATICS" for b in math_books)

    # Search filter
    res_search = client.get("/api/library/books?search=Bloch")
    assert res_search.status_code == 200
    assert any(b["author"] == "Joshua Bloch" for b in res_search.json())


def test_issue_book_and_inventory_decrement(client: TestClient):
    # Ensure student exists
    student_res = client.post(
        "/api/students",
        json={
            "first_name": "Alan",
            "last_name": "Turing",
            "email": "alan.turing.lib@institute.edu",
            "department_id": 1,
            "dob": "2003-06-23",
            "gender": "Male",
        },
    )
    assert student_res.status_code == 201
    student_id = student_res.json()["id"]

    # Accession a single-copy monograph
    book_res = client.post(
        "/api/library/books",
        json={
            "isbn": "978-0262033848",
            "title": "Introduction to Algorithms (CLRS)",
            "author": "Cormen, Leiserson, Rivest, Stein",
            "category": "COMPUTER_SCIENCE",
            "total_copies": 1,
            "shelf_location": "Stack CS-Reference",
        },
    )
    book_id = book_res.json()["id"]

    # Issue book
    issue_payload = {
        "book_id": book_id,
        "student_id": student_id,
        "issue_date": "2026-10-10",
        "due_date": "2026-10-24",
        "remarks": "Algorithms research project checkout",
    }
    issue_res = client.post("/api/library/issue", json=issue_payload)
    assert issue_res.status_code == 201
    loan = issue_res.json()
    assert loan["status"] == "ISSUED"
    assert loan["book_id"] == book_id
    assert loan["student_id"] == student_id

    # Verify inventory copy was decremented to 0
    book_check = client.get(f"/api/library/books/{book_id}").json()
    assert book_check["available_copies"] == 0

    # Attempting to issue again should fail due to 0 availability
    fail_res = client.post("/api/library/issue", json=issue_payload)
    assert fail_res.status_code == 400
    assert "No copies" in fail_res.json()["detail"]


def test_return_book_and_inventory_increment(client: TestClient):
    # Fetch active loans
    loans_res = client.get("/api/library/loans?status=ISSUED")
    assert loans_res.status_code == 200
    loans = loans_res.json()
    assert len(loans) >= 1
    active_loan = loans[0]
    loan_id = active_loan["id"]
    book_id = active_loan["book_id"]

    # Process return
    return_payload = {
        "return_date": "2026-10-20",
        "fine_amount": 5.0,
        "remarks": "Returned in good condition, assessed late fee",
    }
    return_res = client.post(f"/api/library/return/{loan_id}", json=return_payload)
    assert return_res.status_code == 200
    returned_loan = return_res.json()
    assert returned_loan["status"] == "RETURNED"
    assert returned_loan["fine_amount"] == 5.0

    # Verify available copies incremented back
    book_check = client.get(f"/api/library/books/{book_id}").json()
    assert book_check["available_copies"] >= 1


def test_library_stats_and_html_view(client: TestClient):
    stats_res = client.get("/api/library/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_titles"] >= 1
    assert stats["total_copies"] >= 1
    assert stats["total_fines_collected"] >= 0.0

    # Test SSR HTML Page
    html_res = client.get("/library")
    assert html_res.status_code == 200
    has_title = (
        "Library &amp; Digital Circulation" in html_res.text
        or "Library & Digital Circulation" in html_res.text
    )
    assert has_title
    assert "Effective Java" in html_res.text
