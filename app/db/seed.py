from app.db.database import SessionLocal, init_db
from app.db.models import Employee, SecurityLog


def seed_data() -> None:
    init_db()
    db = SessionLocal()

    test_employees = [
        Employee(
            email="sarah.chen@risk-trust.com",
            name="Sarah Chen",
            department="Design",
            account_status="locked",
            licenses=["Slack", "Google Workspace"],
        ),
        Employee(
            email="david.kim@risk-trust.com",
            name="David Kim",
            department="Engineering",
            account_status="active",
            licenses=["Slack", "GitHub"],
        ),
        Employee(
            email="mike.ross@risk-trust.com",
            name="Mike Ross",
            department="Sales",
            account_status="active",
            licenses=["Slack", "Salesforce"],
        ),
        Employee(
            email="elena.vance@risk-trust.com",
            name="Elena Vance",
            department="Product",
            account_status="locked",
            licenses=["Slack", "Jira"],
        ),
    ]

    test_logs = [
        SecurityLog(
            employee_email="sarah.chen@risk-trust.com",
            event_type="FAILED_LOGIN",
            details="Account locked after 5 failed password attempts from known office IP (10.0.1.42).",
        ),
        SecurityLog(
            employee_email="elena.vance@risk-trust.com",
            event_type="SUSPICIOUS_IP",
            details="Account locked due to brute-force login attempts from unrecognized foreign IP (185.220.101.4).",
        ),
        SecurityLog(
            employee_email="david.kim@risk-trust.com",
            event_type="LOGIN_SUCCESS",
            details="Normal SSO authentication from corporate device.",
        ),
    ]

    try:
        for emp in test_employees:
            exists = db.query(Employee).filter(Employee.email == emp.email).first()
            if not exists:
                db.add(emp)

        if db.query(SecurityLog).count() == 0:
            db.add_all(test_logs)

        db.commit()
        print("Database initialized and seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
