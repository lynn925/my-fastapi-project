# 数据库连接配置
from typing import Annotated

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Session

# SQLite 数据库（适合开发）
# 注意是相对路径，必须在项目目录下启动，否则 db 文件会落到别处
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# 创建会话工程
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# 创建基类
# SQLAlchemy 2.0 的 DeclarativeBase 必须被继承，不能直接实例化。
# 直接写 Base = DeclarativeBase() 拿到的是一个没有 registry/metadata 的普通实例，
# 后面 class User(Base) 会直接报错。
class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI 依赖：拿到一个数据库会话，请求结束后关闭。

    放在 database.py 里，是为了让 auth.py 也能用（auth.py 同样需要查 users 表），
    同时避免 auth.py 和 main.py 互相 import 形成循环。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]
