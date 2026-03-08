from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base  

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False) 
    firstname = Column(String(100), nullable=True)
    lastname  = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True) 
    
    # Relations (Pluriel car 1 User -> N éléments)
    patches = relationship("Patch", back_populates="user")
    executions = relationship("PatchExecution", back_populates="user") 
    prepatches = relationship("PrePatch", back_populates="user")

    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"