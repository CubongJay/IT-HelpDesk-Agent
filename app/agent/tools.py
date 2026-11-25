from app.db.database import SessionLocal
from app.db.models import Employee, SecurityLog, AuditLog
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig


def _format_employee(emp: Employee) -> str:
    licenses = ", ".join(emp.licenses) if emp.licenses else "None"
    return (
        f"Name: {emp.name}\n"
        f"Email: {emp.email}\n"
        f"Department: {emp.department}\n"
        f"Account Status: {emp.account_status}\n"
        f"Active Licenses: {licenses}"
    )


def _format_security_logs(email: str, logs: list[SecurityLog]) -> str:
    lines = [f"Security logs for {email}:"]
    for log in logs:
        timestamp = log.created_at.strftime("%Y-%m-%d %H:%M UTC")
        lines.append(f"- [{timestamp}] {log.event_type}: {log.details}")
    return "\n".join(lines)


@tool
def get_employee_records(email: str) -> str:
    """
    This tools gets and return employees records matching the given email.
    """
    clean_email = email.strip().lower()

    with SessionLocal() as db:
        employee = db.query(Employee).filter(Employee.email == clean_email).first()
        if not employee:
            return f"ERROR: No employee found with this email '{clean_email}'"

        return _format_employee(employee)


@tool
def get_security_logs(email: str) -> str:
    """Retrieve recent authentication and security logs for an employee by email to investigate locked accounts or suspicious login activity."""

    clean_email = email.strip().lower()
    with SessionLocal() as db:
        logs = db.query(SecurityLog).filter(SecurityLog.employee_email == clean_email)

        if not logs:
            return f"No logs were found for the employee - '{clean_email}'"

        return _format_security_logs(clean_email, logs)


VALID_LICENSES = {"Figma", "JetBrains", "Salesforce", "Slack", "GitHub", "Jira"}


@tool
def unlock_account(email: str, config: RunnableConfig) -> str:
    """Unlock a locked corporate user account. HIGH RISK: Requires admin approval."""
    clean_email = email.strip().lower()
    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id", "unknown-thread")
    approved_by = configurable.get("approved_by", "IT Admin")

    with SessionLocal() as db:
        employee = db.query(Employee).filter(Employee.email == clean_email).first()
        if not employee:
            return f"ERROR: Cannot unlock unknown employee '{clean_email}'."

        if employee.account_status == "active":
            return f"INFO: Account for '{clean_email}' is already active."

        employee.account_status = "active"
        db.add(
            AuditLog(
                thread_id=thread_id,
                action_name="unlock_account",
                action_args={"email": clean_email},
                approved_by=approved_by,
            )
        )
        db.commit()
        return (
            f"SUCCESS: Account for {employee.name} ({clean_email}) has been unlocked."
        )


@tool
def provision_license(email: str, software: str, config: RunnableConfig) -> str:
    """Provision a paid software license to an employee. HIGH RISK: Requires admin approval."""
    clean_email = email.strip().lower()
    clean_software = software.strip()

    if clean_software not in VALID_LICENSES:
        return (
            f"ERROR: Invalid software '{clean_software}'. "
            f"Valid options are: {sorted(VALID_LICENSES)}"
        )

    configurable = config.get("configurable", {})
    thread_id = configurable.get("thread_id", "unknown-thread")
    approved_by = configurable.get("approved_by", "IT Admin")

    with SessionLocal() as db:
        employee = db.query(Employee).filter(Employee.email == clean_email).first()
        if not employee:
            return f"ERROR: Employee '{clean_email}' not found."

        if clean_software in employee.licenses:
            return f"INFO: {employee.name} ({clean_email}) already has a {clean_software} license."

        employee.licenses = [*employee.licenses, clean_software]
        db.add(
            AuditLog(
                thread_id=thread_id,
                action_name="provision_license",
                action_args={"email": clean_email, "software": clean_software},
                approved_by=approved_by,
            )
        )
        db.commit()
        return f"SUCCESS: Provisioned {clean_software} license for {employee.name} ({clean_email})."


SAFE_TOOLS = [get_employee_records, get_security_logs]
RISKY_TOOLS = [unlock_account, provision_license]
ALL_TOOLS = SAFE_TOOLS + RISKY_TOOLS
