from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey,Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("patch_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    level = Column(String(20), nullable=False, default="INFO", index=True)
    phase = Column(String(50), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    source = Column(String(100), nullable=True)
    
    # Relations
    execution = relationship("PatchExecution", back_populates="logs")

    def __repr__(self):
        return f"<ExecutionLog(id={self.id}, level='{self.level}')>"