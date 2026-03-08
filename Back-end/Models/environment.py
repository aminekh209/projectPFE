from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, text
from sqlalchemy.orm import relationship
from database import Base

class Environment(Base):
    __tablename__ = "environments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False) 
    env_type = Column(String(50), nullable=True)  
    client_id = Column(Integer, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))

    # Relations
    client = relationship("Client", back_populates="environments")
    servers = relationship("Server", back_populates="environment")
    patches = relationship("Patch", back_populates="environment")

    def __repr__(self):
        return f"<Environment(name='{self.name}', type='{self.env_type}')>"