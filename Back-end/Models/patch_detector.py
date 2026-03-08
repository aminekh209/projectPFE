from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, BigInteger, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class PatchDetector(Base):
    __tablename__ = "patch_detectors"

    id = Column(Integer, primary_key=True, index=True)
    patch_id = Column(Integer, ForeignKey("patchs.id", ondelete="CASCADE"), nullable=False, index=True)
    server_id = Column(Integer, ForeignKey("servers.id", ondelete="CASCADE"), nullable=True, index=True) 
    
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=True) 
    file_type = Column(String(100), nullable=True, index=True) 
    actions = Column(String(500), nullable=True)
    # Relations
    patch = relationship("Patch", back_populates="detectors")
    server = relationship("Server", back_populates="detectors")

    def __repr__(self):
        return f"<PatchDetector(id={self.id}, action='{self.action}')>"