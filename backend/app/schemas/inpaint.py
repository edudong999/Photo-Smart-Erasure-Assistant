from datetime import datetime
from pydantic import BaseModel


class SubmitResponse(BaseModel):
    task_id: str
    status: str
    created_at: datetime
    expires_at: datetime
