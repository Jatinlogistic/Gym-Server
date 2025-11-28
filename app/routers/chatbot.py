from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.ai.chatbot import ChatbotAssistant
from app.models import UserProfile

router = APIRouter(prefix="/profile/chat", tags=["Chatbot"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/")
def chat_with_ai(data: dict, db: Session = Depends(get_db)):
    """
    Chatbot endpoint.
    Input: {"email": "user@example.com", "message": "..."} OR {"user_id": 1, "message": "..."}
    """
    email = data.get("email")
    user_id = data.get("user_id")
    message = data.get("message")

    if not message:
        raise HTTPException(status_code=400, detail="Message is required")

    if not email and not user_id:
        raise HTTPException(status_code=400, detail="Email or user_id is required")

    if not email and user_id:
        user = db.query(UserProfile).filter(UserProfile.userid == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        email = str(user.email)

    if not email:
         raise HTTPException(status_code=400, detail="Email is required")

    assistant = ChatbotAssistant()
    response = assistant.get_chat_response(email, message, db)
    
    return {"response": response}
