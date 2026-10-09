from decimal import Decimal
from pydantic import BaseModel, Field

class TaskCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = ""
    category: str = "VISIT"
    reward_usd: Decimal = Field(gt=0, le=1000)
    verification_mode: str = "manual"
    target_url: str | None = None
    active: bool = True

class CompleteTaskRequest(BaseModel):
    task_id: int
    proof: str = Field(default="", max_length=2000)

class WithdrawalRequest(BaseModel):
    amount_usd: Decimal = Field(gt=0, le=10000)
    method: str = Field(min_length=2, max_length=40)
    payout_details: str = Field(min_length=3, max_length=1000)

class ReviewRequest(BaseModel):
    action: str
    note: str = ""
