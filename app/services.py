from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import User, Task, TaskCompletion, LedgerEntry, Withdrawal
from .config import settings

async def get_or_create_referral(db: AsyncSession, new_user: User, referrer_telegram_id: int | None):
    if not referrer_telegram_id or referrer_telegram_id == new_user.telegram_id or new_user.referred_by_id:
        return
    result = await db.execute(select(User).where(User.telegram_id == referrer_telegram_id))
    referrer = result.scalar_one_or_none()
    if referrer:
        new_user.referred_by_id = referrer.id
        await db.commit()

async def activate_referral_bonus(db: AsyncSession, user: User):
    if user.referral_activated or not user.referred_by_id:
        return
    ref_result = await db.execute(select(User).where(User.id == user.referred_by_id).with_for_update())
    referrer = ref_result.scalar_one_or_none()
    if not referrer:
        return
    ref = f"referral:{user.id}"
    exists = await db.execute(select(LedgerEntry).where(LedgerEntry.reference == ref))
    if exists.scalar_one_or_none():
        user.referral_activated = True
        return
    bonus = settings.referral_bonus_usd
    referrer.pending_balance += bonus
    db.add(LedgerEntry(user_id=referrer.id, amount_usd=bonus, entry_type="referral_pending",
                       reference=ref, note=f"Referral bonus for user {user.id}"))
    user.referral_activated = True

async def request_task_completion(db: AsyncSession, user: User, task_id: int, proof: str):
    result = await db.execute(select(Task).where(Task.id == task_id, Task.active.is_(True)))
    task = result.scalar_one_or_none()
    if not task:
        return None, "Task not found or inactive"
    # One completion per user/task. A task is pending until verified by a trusted provider or admin.
    key = f"task:{task.id}:user:{user.id}"
    existing = await db.execute(select(TaskCompletion).where(TaskCompletion.idempotency_key == key))
    if existing.scalar_one_or_none():
        return None, "You have already submitted this task"
    completion = TaskCompletion(user_id=user.id, task_id=task.id, proof=proof, idempotency_key=key)
    db.add(completion)
    await db.commit()
    await db.refresh(completion)
    return completion, None

async def approve_task(db: AsyncSession, completion: TaskCompletion):
    if completion.status != "pending":
        return False
    task_result = await db.execute(select(Task).where(Task.id == completion.task_id))
    task = task_result.scalar_one()
    user_result = await db.execute(select(User).where(User.id == completion.user_id).with_for_update())
    user = user_result.scalar_one()
    ref = f"task-completion:{completion.id}"
    already = await db.execute(select(LedgerEntry).where(LedgerEntry.reference == ref))
    if already.scalar_one_or_none():
        return False
    user.balance += task.reward_usd
    db.add(LedgerEntry(user_id=user.id, amount_usd=task.reward_usd, entry_type="task_reward",
                       reference=ref, note=f"Verified task: {task.title}"))
    completion.status = "approved"
    completion.reviewed_at = datetime.now(timezone.utc)
    await activate_referral_bonus(db, user)
    await db.commit()
    return True
