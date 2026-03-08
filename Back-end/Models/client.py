from sqlalchemy import Column, Integer, String, DateTime, text, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))

    # Relations
    environments = relationship("Environment", back_populates="client", cascade="all, delete-orphan")
    servers = relationship("Server", back_populates="client")
    patches = relationship("Patch", back_populates="client")

    def __repr__(self):
        return f"<Client(name='{self.name}')>"