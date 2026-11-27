from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException
from langchain_core.messages import HumanMessage, ToolMessage
from sqlalchemy.orm import Session

from app.agent.graph import it_agent_graph
from app.agent.guardrails import check_input_guardrails, check_tool_call_guardrails
from app.db.database import get_db, init_db
from app.db.models import AuditLog, Ticket
from app.schemas import ApprovalRequest, ChatRequest, ChatResponse

app = FastAPI(title="Autonomous IT Helpdesk Agent", version="1.0.0")


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)) -> ChatResponse:
    is_safe, block_reson = check_input_guardrails(req.message)
    if not is_safe:
        return ChatResponse(
            thread_id=req.thread_id,
            status="blocked",
            reply=block_reson or "Request blocked by security guardrails",
        )
    ticket = db.query(Ticket).filter(Ticket.thread_id == req.thread_id).first()
    if not ticket:
        ticket = Ticket(
            thread_id=req.thread_id,
            employee_email="unknown",
            issue_summary=req.message[:250],
            status="open",
        )
        db.add(ticket)
        db.commit()

    config = {"configurable": {"thread_id": req.thread_id}}
    result = it_agent_graph.invoke(
        {"messages": [HumanMessage(content=req.message)]},
        config=config,
    )

    snapshot = it_agent_graph.get_state(config)
    last_message = result["messages"][-1]

    if snapshot.next and "risky_tools" in snapshot.next:
        pending_calls = [
            {"id": tc["id"], "name": tc["name"], "args": tc["args"]}
            for tc in getattr(last_message, "tool_calls", [])
        ]
        is_valid, tool_block_reason = check_tool_call_guardrails(pending_calls)
        if not is_valid:
            ticket.status = "blocked"
            db.commit()
            return ChatResponse(
                thread_id=req.thread_id,
                status="blocked",
                reply=tool_block_reason or "Action blocked by tool guardrails.",
            )
        ticket.status = "pending_approval"
        ticket.pending_action = {"tool_calls": pending_calls}
        db.commit()

        return ChatResponse(
            thread_id=req.thread_id,
            status="pending_approval",
            reply="Your request has been verified and queued for IT Administrator approval.",
            pending_actions=pending_calls,
        )

    ticket.status = "resolved"
    ticket.pending_action = None
    db.commit()

    return ChatResponse(
        thread_id=req.thread_id,
        status="completed",
        reply=str(last_message.content),
    )


@app.post("/tickets/{thread_id}/approve", response_model=ChatResponse)
def approve_ticket(
    thread_id: str,
    req: ApprovalRequest,
    db: Session = Depends(get_db),
) -> ChatResponse:
    ticket = db.query(Ticket).filter(Ticket.thread_id == thread_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    config = {
        "configurable": {
            "thread_id": thread_id,
            "approved_by": req.approved_by,
        }
    }
    snapshot = it_agent_graph.get_state(config)

    if not snapshot.next or "risky_tools" not in snapshot.next:
        raise HTTPException(
            status_code=400,
            detail="No pending high-risk action awaiting approval for this thread.",
        )

    if req.approved:
        result = it_agent_graph.invoke(None, config=config)
        ticket.status = "resolved"
        ticket.pending_action = None
        db.commit()

        final_reply = str(result["messages"][-1].content)
        return ChatResponse(
            thread_id=thread_id,
            status="completed",
            reply=final_reply,
        )

    last_message = snapshot.values["messages"][-1]
    rejection_messages = [
        ToolMessage(
            tool_call_id=tc["id"],
            content=f"ERROR: Action '{tc['name']}' was rejected by {req.approved_by}.",
        )
        for tc in getattr(last_message, "tool_calls", [])
    ]
    it_agent_graph.update_state(
        config, {"messages": rejection_messages}, as_node="risky_tools"
    )
    result = it_agent_graph.invoke(None, config=config)

    ticket.status = "rejected"
    ticket.pending_action = None
    db.commit()

    return ChatResponse(
        thread_id=thread_id,
        status="rejected",
        reply=str(result["messages"][-1].content),
    )


@app.get("/tickets/{thread_id}")
def get_ticket_details(thread_id: str, db: Session = Depends(get_db)) -> dict:
    ticket = db.query(Ticket).filter(Ticket.thread_id == thread_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    audits = db.query(AuditLog).filter(AuditLog.thread_id == thread_id).all()
    return {
        "thread_id": ticket.thread_id,
        "status": ticket.status,
        "issue_summary": ticket.issue_summary,
        # "pending_action": ticket.pending_action,
        "audit_logs": [
            {
                "action_name": a.action_name,
                "action_args": a.action_args,
                "approved_by": a.approved_by,
                "executed_at": a.created_at,
            }
            for a in audits
        ],
    }
