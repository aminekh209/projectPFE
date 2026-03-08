from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base  # Importez votre instance de Base




class PrePatch(Base):
    __tablename__ = "prepatchs"

    id = Column(Integer, primary_key=True, index=True)
    patch_id = Column(Integer, ForeignKey("patchs.id", ondelete="CASCADE"), nullable=False, index=True)
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True) 
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True, index=True) 
    criticality = Column(String(50), nullable=True) 
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    patch = relationship("Patch", back_populates="prepatches")
    server = relationship("Server", back_populates="prepatches")
    user = relationship("User", back_populates="prepatches")

    def __repr__(self):
        return f"<PrePatch(id={self.id}, patch_id={self.patch_id}, category='{self.category}')>"