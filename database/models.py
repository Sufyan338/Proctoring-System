"""
Database models for the Proctoring System
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from config import DATABASE_URL

Base = declarative_base()

# Create engine
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class User(Base):
    """User model for students and admins"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="student")  # student, admin, proctor
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    exams = relationship("ExamSession", back_populates="student")
    alerts = relationship("ProctorAlert", back_populates="student")

class Exam(Base):
    """Exam model"""
    __tablename__ = "exams"
    
    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(String, unique=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    duration_minutes = Column(Integer)
    total_questions = Column(Integer)
    passing_score = Column(Float, default=60.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    sessions = relationship("ExamSession", back_populates="exam")

class ExamSession(Base):
    """Exam session for each student taking an exam"""
    __tablename__ = "exam_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    exam_id = Column(Integer, ForeignKey("exams.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    score = Column(Float, nullable=True)
    status = Column(String, default="in_progress")  # in_progress, completed, abandoned
    total_alerts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    student = relationship("User", back_populates="exams")
    exam = relationship("Exam", back_populates="sessions")
    proctor_alerts = relationship("ProctorAlert", back_populates="session")

class ProctorAlert(Base):
    """Alert raised by proctoring system"""
    __tablename__ = "proctor_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("exam_sessions.id"))
    alert_type = Column(String)  # face_not_visible, multiple_faces, unusual_behavior, etc.
    severity = Column(String)  # LOW, MEDIUM, HIGH
    description = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)
    image_path = Column(String, nullable=True)
    action_taken = Column(String, nullable=True)
    
    student = relationship("User", back_populates="alerts")
    session = relationship("ExamSession", back_populates="proctor_alerts")

class Question(Base):
    """Question model for exams"""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(String, unique=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"))
    question_text = Column(Text)
    question_type = Column(String)  # multiple_choice, short_answer, essay
    options = Column(Text, nullable=True)  # JSON format for MCQ
    correct_answer = Column(String)
    marks = Column(Float, default=1.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class Answer(Base):
    """Student's answer to a question"""
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(String, unique=True, index=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_text = Column(Text)
    is_correct = Column(Boolean, nullable=True)
    marks_obtained = Column(Float, nullable=True)
    answered_at = Column(DateTime, default=datetime.utcnow)

class ActivityLog(Base):
    """Activity log for audit trail"""
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=True)
    action = Column(String)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

# Create all tables
def init_db():
    """Initialize database"""
    Base.metadata.create_all(bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
