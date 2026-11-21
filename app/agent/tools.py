from app.db.database import SessionLocal
from app.db.models import Employee
from langchain_core.tools import tool


def _format_employee(emp: Employee) -> str:
    licenses = ", ".join(emp.licenses) if emp.licenses else "None"
    return (
        f"Name: {emp.name}\n"
        f"Email: {emp.email}\n"
        f"Department: {emp.department}\n"
        f"Account Status: {emp.account_status}\n"
        f"Active Licenses: {licenses}"
    )


@tool
def get_employee_records(email: str) -> str:
    """
    This tools gets and return employees records matching the given email.
    """
    clean_email = email.strip().lower()

    with SessionLocal as db:
        employee = db.query(Employee).filter(Employee.email == clean_email).first()
        if not employee:
            return f"ERROR: No employee found with this email '{clean_email}'"

        return _format_employee(employee)
