from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from src.models import get_db
from src.api.auth import get_current_user
from src.models.user import User
from src.services.coach_chat_service import (
    get_chat_history,
    handle_user_chat_message,
    apply_chat_discussed_changes
)

router = APIRouter(prefix="/chat", tags=["chat"])

class SendMessageRequest(BaseModel):
    message: str

@router.get("/history")
def fetch_chat_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        messages = get_chat_history(current_user.id, db)
        return {
            "status": "success",
            "messages": [m.dict() for m in messages]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/message")
def post_chat_message(
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not payload.message or not payload.message.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message text cannot be empty"
        )
    try:
        reply = handle_user_chat_message(current_user.id, payload.message.strip(), db)
        return {
            "status": "success",
            "reply": reply
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process AI Coach chat: {str(e)}"
        )

@router.post("/apply-changes")
def apply_chat_changes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        res = apply_chat_discussed_changes(current_user.id, db)
        return res
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to apply plan changes: {str(e)}"
        )
