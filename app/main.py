from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from .config import settings
from .db import init_db, get_db
from .models import User, Task, TaskCompletion, LedgerEntry, Withdrawal
from .security import current_user, admin_user
from .schemas import TaskCreate, CompleteTaskRequest, WithdrawalRequest, ReviewRequest
from .services import request_task_completion, approve_task

app = FastAPI(title=settings.app_name, version="0.1.0")
WEB = Path(__file__).resolve().parent.parent / "web"

@app.on_event("startup")
async def startup():
    await init_db()

app.mount("/static", StaticFiles(directory=str(WEB)), name="static")

@app.get("/")
async def mini_app():
    return FileResponse(WEB / "index.html")

@app.get("/admin")
async def admin_page():
    return FileResponse(WEB / "admin.html")

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/api/me")
async def me(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    joined = await db.scalar(select(func.count(User.id)).where(User.referred_by_id == user.id))
    return {"telegram_id": user.telegram_id, "username": user.username, "first_name": user.first_name,
            "balance_usd": str(user.balance), "pending_balance_usd": str(user.pending_balance),
            "currency": user.currency, "language": user.language, "referrals": joined or 0}

@app.get("/api/tasks")
async def tasks(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task).where(Task.active.is_(True)).order_by(Task.id.desc()))
    return [{"id": t.id, "title": t.title, "description": t.description, "category": t.category,
             "reward_usd": str(t.reward_usd), "verification_mode": t.verification_mode,
             "target_url": t.target_url} for t in result.scalars().all()]

@app.post("/api/tasks/complete")
async def complete_task(payload: CompleteTaskRequest, user: User = Depends(current_user),
                        db: AsyncSession = Depends(get_db)):
    completion, error = await request_task_completion(db, user, payload.task_id, payload.proof)
    if error:
        raise HTTPException(409, error)
    return {"status": "pending", "message": "Submitted for verification. Reward is not credited until verified.",
            "completion_id": completion.id}

@app.get("/api/history")
async def history(user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(LedgerEntry).where(LedgerEntry.user_id == user.id).order_by(LedgerEntry.id.desc()).limit(100))
    return [{"amount_usd": str(x.amount_usd), "type": x.entry_type, "note": x.note,
             "created_at": x.created_at.isoformat()} for x in result.scalars().all()]

@app.post("/api/withdrawals")
async def withdraw(payload: WithdrawalRequest, user: User = Depends(current_user), db: AsyncSession = Depends(get_db)):
    locked = await db.execute(select(User).where(User.id == user.id).with_for_update())
    user = locked.scalar_one()
    if payload.amount_usd < settings.min_withdraw_usd:
        raise HTTPException(400, f"Minimum withdrawal is ${settings.min_withdraw_usd}")
    if payload.amount_usd > user.balance:
        raise HTTPException(400, "Insufficient available balance")
    user.balance -= payload.amount_usd
    w = Withdrawal(user_id=user.id, amount_usd=payload.amount_usd, method=payload.method,
                   payout_details=payload.payout_details, status="pending")
    db.add(w)
    db.add(LedgerEntry(user_id=user.id, amount_usd=-payload.amount_usd, entry_type="withdrawal_hold",
                       reference=f"withdrawal-hold:{user.telegram_id}:{datetime.now(timezone.utc).timestamp()}",
                       note="Funds held while withdrawal is reviewed"))
    await db.commit()
    await db.refresh(w)
    return {"id": w.id, "status": w.status, "message": "Withdrawal request submitted for admin review"}

# Admin endpoints
@app.get("/api/admin/summary")
async def admin_summary(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    users = await db.scalar(select(func.count(User.id))) or 0
    tasks_count = await db.scalar(select(func.count(Task.id))) or 0
    pending = await db.scalar(select(func.count(Withdrawal.id)).where(Withdrawal.status == "pending")) or 0
    completions = await db.scalar(select(func.count(TaskCompletion.id)).where(TaskCompletion.status == "pending")) or 0
    return {"users": users, "tasks": tasks_count, "pending_withdrawals": pending, "pending_completions": completions}

@app.get("/api/admin/users")
async def admin_users(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.id.desc()).limit(200))
    return [{"id": u.id, "telegram_id": u.telegram_id, "username": u.username, "balance_usd": str(u.balance),
             "blocked": u.is_blocked, "created_at": u.created_at.isoformat()} for u in result.scalars().all()]

@app.post("/api/admin/tasks")
async def create_task(payload: TaskCreate, admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    task = Task(**payload.model_dump())
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"id": task.id, "title": task.title}

@app.get("/api/admin/completions")
async def pending_completions(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskCompletion).where(TaskCompletion.status == "pending").order_by(TaskCompletion.id))
    return [{"id": c.id, "user_id": c.user_id, "task_id": c.task_id, "proof": c.proof, "created_at": c.created_at.isoformat()} for c in result.scalars().all()]

@app.post("/api/admin/completions/{completion_id}/review")
async def review_completion(completion_id: int, payload: ReviewRequest, admin: User = Depends(admin_user),
                           db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(TaskCompletion).where(TaskCompletion.id == completion_id).with_for_update())
    completion = result.scalar_one_or_none()
    if not completion:
        raise HTTPException(404, "Completion not found")
    if payload.action == "approve":
        ok = await approve_task(db, completion)
        if not ok:
            raise HTTPException(409, "Completion is not pending or already credited")
        return {"ok": True, "status": "approved"}
    if payload.action == "reject" and completion.status == "pending":
        completion.status = "rejected"
        completion.reviewed_at = datetime.now(timezone.utc)
        await db.commit()
        return {"ok": True, "status": "rejected"}
    raise HTTPException(400, "Action must be approve or reject on a pending item")

@app.get("/api/admin/withdrawals")
async def admin_withdrawals(admin: User = Depends(admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Withdrawal).where(Withdrawal.status == "pending").order_by(Withdrawal.id))
    return [{"id": w.id, "user_id": w.user_id, "amount_usd": str(w.amount_usd), "method": w.method,
             "payout_details": w.payout_details, "created_at": w.created_at.isoformat()} for w in result.scalars().all()]

@app.post("/api/admin/withdrawals/{withdrawal_id}/review")
async def review_withdrawal(withdrawal_id: int, payload: ReviewRequest, admin: User = Depends(admin_user),
                            db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Withdrawal).where(Withdrawal.id == withdrawal_id).with_for_update())
    w = result.scalar_one_or_none()
    if not w:
        raise HTTPException(404, "Withdrawal not found")
    if w.status != "pending":
        raise HTTPException(409, "Withdrawal already reviewed")
    if payload.action == "approve":
        w.status = "approved"
    elif payload.action == "reject":
        ures = await db.execute(select(User).where(User.id == w.user_id).with_for_update())
        user = ures.scalar_one()
        user.balance += w.amount_usd
        w.status = "rejected"
        db.add(LedgerEntry(user_id=user.id, amount_usd=w.amount_usd, entry_type="withdrawal_refund",
                           reference=f"withdrawal-refund:{w.id}", note="Withdrawal rejected; funds returned"))
    else:
        raise HTTPException(400, "Action must be approve or reject")
    w.admin_note = payload.note
    w.reviewed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"ok": True, "status": w.status}
