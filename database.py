"""
Database models for user authentication and policy management.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import bcrypt

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    policies = relationship("Policy", back_populates="user")
    tickets = relationship("Ticket", back_populates="user", foreign_keys="Ticket.user_id")
    call_summaries = relationship("CallSummary", back_populates="user")
    interventions = relationship("AdminIntervention", back_populates="admin", foreign_keys="AdminIntervention.admin_id")
    
    def verify_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), self.hashed_password.encode('utf-8'))
    
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


class Policy(Base):
    __tablename__ = "policies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    policy_number = Column(String(50), unique=True, index=True, nullable=False)
    policy_type = Column(String(50), nullable=False)  # auto, home, health, life
    status = Column(String(20), default="active")  # active, expired, cancelled
    premium_amount = Column(Float, nullable=False)
    coverage_amount = Column(Float, nullable=False)
    deductible = Column(Float, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    policy_details = Column(JSON)  # Additional policy-specific details
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="policies")
    tickets = relationship("Ticket", back_populates="policy")


class Ticket(Base):
    __tablename__ = "tickets"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    policy_id = Column(Integer, ForeignKey("policies.id"))
    ticket_number = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    category = Column(String(50))  # claim, billing, coverage_question, complaint
    priority = Column(String(20), default="medium")  # low, medium, high, urgent
    status = Column(String(20), default="open")  # open, in_progress, resolved, closed
    resolution = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    assigned_admin_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    user = relationship("User", back_populates="tickets", foreign_keys=[user_id])
    policy = relationship("Policy", back_populates="tickets")
    assigned_admin = relationship("User", foreign_keys=[assigned_admin_id])


class CallSummary(Base):
    __tablename__ = "call_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    call_date = Column(DateTime, default=datetime.utcnow)
    duration_seconds = Column(Integer)
    topic = Column(String(255))
    summary = Column(Text, nullable=False)
    sentiment = Column(String(20))  # positive, neutral, negative, distressed
    key_points = Column(JSON)  # List of key discussion points
    action_items = Column(JSON)  # List of follow-up actions
    requires_followup = Column(Boolean, default=False)
    conversation_transcript = Column(JSON)  # Full conversation history
    
    # Relationships
    user = relationship("User", back_populates="call_summaries")


class AdminIntervention(Base):
    __tablename__ = "admin_interventions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    admin_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trigger_reason = Column(String(255), nullable=False)  # Why AI requested intervention
    ai_confidence_score = Column(Float)  # AI's confidence in handling the query
    conversation_context = Column(JSON)  # Conversation history at intervention
    status = Column(String(20), default="pending")  # pending, active, resolved
    admin_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[admin_id])


# Database connection
DATABASE_URL = "sqlite:///./insurance_system.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
