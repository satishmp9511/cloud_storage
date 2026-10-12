from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    folders = relationship("FolderRecord", back_populates="owner")
    files = relationship("FileRecord", back_populates="owner")

class FolderRecord(Base):
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    foldername = Column(String, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="folders")
    files = relationship("FileRecord", back_populates="folder")

class FileRecord(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True)
    filepath = Column(String)
    filetype = Column(String)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True) # Kis folder me hai
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="files")
    folder = relationship("FolderRecord", back_populates="files")
