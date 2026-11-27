from pydantic import BaseModel


class ChatRequest(BaseModel):
    thread_id: str
    message: str


class ChatResponse(BaseModel):
    thread_id: str
    status: str
    reply: str
    pending_actions: list[dict] | None = None


class ApprovalRequest(BaseModel):
    approved: bool = True
    approved_by: str = "IT Admin"
