"""Tests for Fee Invoicing, Payment Processing, Receipts, and Financial Audit APIs."""


def test_create_fee_structure(client):
    """Verify standard fee schedule creation for department."""
    payload = {
        "department_id": 1,
        "semester": 1,
        "fee_type": "Tuition Fee",
        "amount": 2500.0,
        "academic_year": "2026-2027",
    }
    res = client.post("/api/finance/fee-structures", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["amount"] == 2500.0
    assert data["fee_type"] == "Tuition Fee"
    assert "department_name" in data


def test_fee_structure_duplicate_rejection(client):
    """Verify duplicate fee structure for same dept/sem/type/year is rejected."""
    payload = {
        "department_id": 1,
        "semester": 1,
        "fee_type": "Tuition Fee",
        "amount": 2800.0,
        "academic_year": "2026-2027",
    }
    res = client.post("/api/finance/fee-structures", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"]


def test_list_fee_structures_filters(client):
    """Verify listing and filtering fee structures."""
    # Add a lab fee structure
    client.post(
        "/api/finance/fee-structures",
        json={
            "department_id": 1,
            "semester": 1,
            "fee_type": "Lab & Computing Fee",
            "amount": 450.0,
            "academic_year": "2026-2027",
        },
    )
    res = client.get("/api/finance/fee-structures?department_id=1&semester=1")
    assert res.status_code == 200
    structures = res.json()
    assert len(structures) >= 2


def test_create_invoice_success(client):
    """Verify issuing a fee invoice for an enrolled student."""
    # Create student
    s_res = client.post(
        "/api/students",
        json={
            "first_name": "Rohan",
            "last_name": "Sharma",
            "email": "rohan.sharma@example.edu",
            "department_id": 1,
            "current_semester": 1,
        },
    )
    student_id = s_res.json()["id"]

    inv_res = client.post(
        "/api/finance/invoices",
        json={
            "student_id": student_id,
            "title": "Fall Semester Tuition",
            "term_name": "Fall 2026",
            "total_amount": 2000.0,
            "due_date": "2026-11-15",
        },
    )
    assert inv_res.status_code == 201
    data = inv_res.json()
    assert data["invoice_no"].startswith("INV-2026-")
    assert data["total_amount"] == 2000.0
    assert data["paid_amount"] == 0.0
    assert data["balance_amount"] == 2000.0
    assert data["status"] == "UNPAID"
    assert data["student_name"] == "Rohan Sharma"


def test_create_invoice_nonexistent_student(client):
    """Verify invoice creation fails if student does not exist."""
    inv_res = client.post(
        "/api/finance/invoices",
        json={
            "student_id": 99999,
            "title": "Fall Tuition",
            "term_name": "Fall 2026",
            "total_amount": 1000.0,
            "due_date": "2026-11-15",
        },
    )
    assert inv_res.status_code == 400
    assert "does not exist" in inv_res.json()["detail"]


def test_partial_payment_and_full_settlement(client):
    """Verify recording installments updates balance and status correctly."""
    # Find student
    s_res = client.get("/api/students?search=Rohan")
    student_id = s_res.json()[0]["id"]

    # Issue a $1500 invoice
    inv_res = client.post(
        "/api/finance/invoices",
        json={
            "student_id": student_id,
            "title": "Hostel & Tuition Combined",
            "term_name": "Fall 2026",
            "total_amount": 1500.0,
            "due_date": "2026-11-20",
        },
    )
    inv_id = inv_res.json()["id"]

    # 1. Partial payment of $500
    pay1_res = client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv_id,
            "amount": 500.0,
            "payment_method": "ONLINE",
            "transaction_ref": "TXN-TEST-001",
        },
    )
    assert pay1_res.status_code == 201
    p1 = pay1_res.json()
    assert p1["payment_no"].startswith("REC-2026-")
    assert p1["new_balance"] == 1000.0
    assert p1["invoice_status"] == "PARTIAL"

    # 2. Check invoice record
    inv_detail_res = client.get(f"/api/finance/invoices/{inv_id}")
    assert inv_detail_res.status_code == 200
    inv_detail = inv_detail_res.json()
    assert inv_detail["paid_amount"] == 500.0
    assert inv_detail["balance_amount"] == 1000.0
    assert inv_detail["status"] == "PARTIAL"
    assert len(inv_detail["payments"]) == 1

    # 3. Pay remaining $1000
    pay2_res = client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv_id,
            "amount": 1000.0,
            "payment_method": "UPI",
            "transaction_ref": "UPI-SETTLE-002",
        },
    )
    assert pay2_res.status_code == 201
    p2 = pay2_res.json()
    assert p2["new_balance"] == 0.0
    assert p2["invoice_status"] == "PAID"

    # 4. Check finalized invoice detail
    inv_final = client.get(f"/api/finance/invoices/{inv_id}").json()
    assert inv_final["status"] == "PAID"
    assert inv_final["paid_amount"] == 1500.0
    assert inv_final["balance_amount"] == 0.0
    assert len(inv_final["payments"]) == 2


def test_payment_exceeding_balance_rejected(client):
    """Verify attempting to pay more than invoice balance is rejected with 400."""
    s_res = client.get("/api/students?search=Rohan")
    student_id = s_res.json()[0]["id"]

    inv_res = client.post(
        "/api/finance/invoices",
        json={
            "student_id": student_id,
            "title": "Library Deposit",
            "term_name": "Fall 2026",
            "total_amount": 200.0,
            "due_date": "2026-11-20",
        },
    )
    inv_id = inv_res.json()["id"]

    # Attempt to pay $250 on a $200 invoice
    pay_res = client.post(
        "/api/finance/payments",
        json={
            "invoice_id": inv_id,
            "amount": 250.0,
            "payment_method": "CASH",
        },
    )
    assert pay_res.status_code == 400
    assert "exceeds outstanding balance" in pay_res.json()["detail"]


def test_payment_on_settled_invoice_rejected(client):
    """Verify payment on an already settled invoice is rejected."""
    s_res = client.get("/api/students?search=Rohan")
    student_id = s_res.json()[0]["id"]

    inv_res = client.post(
        "/api/finance/invoices",
        json={
            "student_id": student_id,
            "title": "ID Card Fee",
            "term_name": "Fall 2026",
            "total_amount": 50.0,
            "due_date": "2026-11-20",
        },
    )
    inv_id = inv_res.json()["id"]

    # Settle in full
    client.post(
        "/api/finance/payments",
        json={"invoice_id": inv_id, "amount": 50.0, "payment_method": "CASH"},
    )

    # Attempt another payment
    extra_pay = client.post(
        "/api/finance/payments",
        json={"invoice_id": inv_id, "amount": 10.0, "payment_method": "CASH"},
    )
    assert extra_pay.status_code == 400
    assert "already fully settled" in extra_pay.json()["detail"]


def test_financial_summary_and_ledger_listing(client):
    """Verify executive financial summary KPIs and payment ledger querying."""
    summary_res = client.get("/api/finance/summary")
    assert summary_res.status_code == 200
    summary = summary_res.json()
    assert summary["total_billed"] > 0
    assert summary["total_collected"] > 0
    assert summary["collection_rate"] >= 0
    assert "recent_payments" in summary

    # List payments ledger
    payments_res = client.get("/api/finance/payments?limit=10")
    assert payments_res.status_code == 200
    payments = payments_res.json()
    assert len(payments) >= 1
    assert "payment_no" in payments[0]
    assert "invoice_no" in payments[0]


def test_view_finance_html_page(client):
    """Verify rendering of the institutional bursar and audit ledger HTML dashboard."""
    res = client.get("/finance")
    assert res.status_code == 200
    assert "Institutional Bursar & Audit Ledger" in res.text
    assert "Fee Invoices Roster" in res.text
    assert "Audit Ledger" in res.text


def test_view_print_receipt_page(client):
    """Verify rendering of printable official fee receipt."""
    # Fetch first available invoice ID
    invoices = client.get("/api/finance/invoices").json()
    assert len(invoices) >= 1
    inv_id = invoices[0]["id"]

    res = client.get(f"/finance/invoices/{inv_id}/print")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    assert "FEE RECEIPT" in res.text
    assert "INSTITUTE MANAGEMENT SYSTEM" in res.text
