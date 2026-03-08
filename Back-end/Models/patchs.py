from sqlalchemy import Column, Integer, String, ForeignKey, BigInteger,Text, DateTime, text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base  # Importez votre instance de Base

class Patch(Base):
    __tablename__ = "patchs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    original_filename = Column(String(50), nullable=False, index=True) 
    description = Column(Text, nullable=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(BigInteger, nullable=True)  
    patch_type = Column(String(50), nullable=False)
    component = Column(String(50), nullable=False)
    status = Column(String(50), server_default='PENDING')
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    
    # Foreign Keys
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True)
    environment_id = Column(Integer, ForeignKey("environments.id"), nullable=True)
    server_id = Column(Integer, ForeignKey("servers.id"), nullable=True)
    # (J'ai supprimé analyse_id ici pour éviter la boucle infinie avec PatchDetector)
    
    # Relations vers les parents
    user = relationship("User", back_populates="patches")
    client = relationship("Client", back_populates="patches")
    environment = relationship("Environment", back_populates="patches")
    server = relationship("Server", back_populates="patches")

    # Relations vers les enfants (cascade)
    prepatches = relationship("PrePatch", back_populates="patch", cascade="all, delete-orphan")
    executions = relationship("PatchExecution", back_populates="patch", cascade="all, delete-orphan")
    detectors = relationship("PatchDetector", back_populates="patch", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Patch(name='{self.name}', status='{self.status}')>"