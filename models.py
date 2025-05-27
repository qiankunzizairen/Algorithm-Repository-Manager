# models.py
"""
ORM 模型定义：使用 SQLAlchemy 定义数据库表结构。
"""
from sqlalchemy import (
    Column, Integer, String, Text, Enum, Float, DateTime, ForeignKey, create_engine
)
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime
import config

# 基类
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    role = Column(Enum('user', 'admin'), default='user', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    algorithms    = relationship('Algorithm', back_populates='owner', cascade='all, delete-orphan')
    comments      = relationship('Comment',   back_populates='user',    cascade='all, delete-orphan')
    admin_logs    = relationship('AdminLog',  back_populates='admin',   cascade='all, delete-orphan')
    download_logs = relationship('DownloadLog', back_populates='user', cascade='all, delete-orphan')

class Algorithm(Base):
    __tablename__ = 'algorithms'
    id          = Column(Integer, primary_key=True)
    title       = Column(String(100), nullable=False)
    description = Column(Text)
    owner_id    = Column(Integer, ForeignKey('users.id'), nullable=False)
    tags        = Column(String(255))
    category    = Column(String(50))
    version     = Column(Integer, default=1)
    code        = Column(Text, nullable=False)
    score       = Column(Float, default=0.0)
    status      = Column(Enum('pending','approved','rejected'), default='pending')
    created_at  = Column(DateTime, default=datetime.utcnow)

    owner        = relationship('User',    back_populates='algorithms')
    comments     = relationship('Comment', back_populates='algorithm', cascade='all, delete-orphan')
    download_logs= relationship('DownloadLog', back_populates='algorithm', cascade='all, delete-orphan')

class Comment(Base):
    __tablename__  = 'comments'
    id              = Column(Integer, primary_key=True)
    algorithm_id    = Column(Integer, ForeignKey('algorithms.id'), nullable=False)
    user_id         = Column(Integer, ForeignKey('users.id'),     nullable=False)
    rating          = Column(Integer)
    content         = Column(Text)
    created_at      = Column(DateTime, default=datetime.utcnow)

    algorithm       = relationship('Algorithm', back_populates='comments')
    user            = relationship('User',      back_populates='comments')

class AdminLog(Base):
    __tablename__ = 'admin_logs'
    id          = Column(Integer, primary_key=True)
    admin_id    = Column(Integer, ForeignKey('users.id'), nullable=False)
    action      = Column(String(100))
    target_type = Column(String(50))
    target_id   = Column(Integer)
    timestamp   = Column(DateTime, default=datetime.utcnow)

    admin       = relationship('User', back_populates='admin_logs')

class DownloadLog(Base):
    __tablename__    = 'download_logs'
    id                = Column(Integer, primary_key=True)
    user_id           = Column(Integer, ForeignKey('users.id'),      nullable=False)
    algorithm_id      = Column(Integer, ForeignKey('algorithms.id'), nullable=False)
    downloaded_at     = Column(DateTime, default=datetime.utcnow)

    user              = relationship('User',      back_populates='download_logs')
    algorithm         = relationship('Algorithm', back_populates='download_logs')

class ScoringStrategy(Base):
    __tablename__    = 'scoring_strategy'
    id                = Column(Integer, primary_key=True)
    func_weight       = Column(Integer)
    comment_weight    = Column(Integer)

# 引擎与会话工厂
engine = create_engine(
    f"mysql+pymysql://{config.APP_DB_USER}:{config.APP_DB_PWD}@{config.DB_HOST}/{config.DB_NAME}?charset=utf8mb4",
    echo=False
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 初始化表
def init_models():
    Base.metadata.create_all(bind=engine)
