from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base  # Importez votre instance de Base




class PatchExecution(Base):
    __tablename__ = "patch_executions"

    id = Column(Integer, primary_key=True, index=True)
    patch_id = Column(Integer, ForeignKey("patchs.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True) 
    
    status = Column(String(50), nullable=False, default="en_attente", index=True)
    phase = Column(String(50), nullable=False, default="préparation", index=True)
    
    # Relations
    patch = relationship("Patch", back_populates="executions")
    user = relationship("User", back_populates="executions")
    server = relationship("Server", back_populates="executions")
    logs = relationship("ExecutionLog", back_populates="execution", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<PatchExecution(id={self.id}, status='{self.status}', phase='{self.phase}')>"