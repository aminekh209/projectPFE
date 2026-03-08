from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Server(Base):
    __tablename__ = "servers"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    environment_id = Column(Integer, ForeignKey("environments.id", ondelete="SET NULL"), nullable=True)
    
    hostname = Column(String(255), nullable=False, unique=True, index=True)
    ip_address = Column(String(45), nullable=False, index=True) 
    server_type = Column(String(50), nullable=False, index=True)
    port = Column(Integer, nullable=False, default=22) 
    is_active = Column(Boolean, default=True, index=True)
    
    # Relations inverses (Singulier pour Parent, Pluriel pour Enfants)
    client = relationship("Client", back_populates="servers")
    environment = relationship("Environment", back_populates="servers")
    
    patches = relationship("Patch", back_populates="server")
    executions = relationship("PatchExecution", back_populates="server")
    prepatches = relationship("PrePatch", back_populates="server")
    detectors = relationship("PatchDetector", back_populates="server")

    def __repr__(self):
        return f"<Server(hostname='{self.hostname}', ip='{self.ip_address}')>"