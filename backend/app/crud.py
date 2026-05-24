from sqlalchemy.orm import Session
from app import models

def get_sessions(db: Session):
    return db.query(models.ChatSession).order_by(models.ChatSession.created_at.desc()).all()

def create_session(db: Session, title: str):
    db_session = models.ChatSession(title=title)
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

def get_messages(db: Session, session_id: int):
    return db.query(models.ChatMessage).filter(models.ChatMessage.session_id == session_id).order_by(models.ChatMessage.created_at.asc()).all()

def add_message(db: Session, session_id: int, role: str, content: str):
    db_message = models.ChatMessage(session_id=session_id, role=role, content=content)
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message

def delete_session(db: Session, session_id: int):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if session:
        db.delete(session)
        db.commit()
    return session

def rename_session(db: Session, session_id: int, title: str):
    session = db.query(models.ChatSession).filter(models.ChatSession.id == session_id).first()
    if session:
        session.title = title
        db.commit()
        db.refresh(session)
    return session
