"""认证工具模块：bcrypt 密码哈希 + JWT 签发/校验 + 「当前用户」依赖。

这个模块只提供能力，不定义路由：
- 路由放在 main.py（和 users / items 那些放在一起）
- 用户数据存在 SQLAlchemy 的 users 表里，不再单独维护一份存储

分层（避免循环 import）：
    database.py  →  engine / Base / get_db
    models.py    →  ORM 模型
    auth.py      →  密码哈希、JWT、get_current_user 依赖（依赖 models + database）
    crud.py      →  数据库操作（依赖 auth 的 hash_password）
    main.py      →  路由（依赖 auth + crud）
"""
import os
from datetime import datetime, timedelta, timezone
from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import models
from database import get_db

# ---------- 配置（生产环境请用环境变量注入 SECRET_KEY） ----------
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-please-change-me")
ALGORITHM = "HS256"  # 对称加密签名，简单够用；需要非对称可换 RS256
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# bcrypt 5.0 起不再静默截断超过 72 字节的密码，而是直接抛 ValueError，
# 所以注册和校验都要自己按字节截断，且两边必须用同一套规则
BCRYPT_MAX_BYTES = 72

# auto_error=False：没有 Authorization 头时返回 None，由我们自己抛 401
# tokenUrl 指向 main.py 里的登录接口，Swagger 的 Authorize 按钮会用它换 token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login", auto_error=False)


# ---------- 密码处理 ----------
# 这里直接用 bcrypt 原生 API，没有用 passlib：
# passlib 1.7.4 在加载后端时会拿一个超长密码做 wraparound bug 自检，
# 而 bcrypt 5.0 不再静默截断超长密码（直接抛 ValueError），于是 passlib 的
# 后端自检会失败，导致所有 passlib 哈希操作都报错。
# 如果你想继续用 passlib，就得把 bcrypt 降到 4.x：pip install "bcrypt<5"


def _prepare(password: str) -> bytes:
    """按字节截断到 72 字节。

    注册和校验必须走同一个规则，否则会出现「注册成功却永远登不上」的情况：
    用户输入 80 个字符时 bcrypt 只存了前 72 个，校验时如果按完整字符串去比就会失败。
    """
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """bcrypt 哈希"""
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """校验密码"""
    try:
        return bcrypt.checkpw(_prepare(password), hashed_password.encode("utf-8"))
    except ValueError:
        # 哈希值本身损坏或格式不对，同样当作校验失败
        return False


# ---------- JWT ----------
def create_access_token(subject: str, expires_delta: timedelta | None = None) -> str:
    """签发 JWT，subject 放用户 id（字符串形式）"""
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    payload = {"sub": subject, "iat": now, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> str:
    """校验 JWT 并取出 subject，失败统一抛 401"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        # 包含令牌过期、签名不对、格式损坏等各种情况
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效或已过期的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌缺少 sub 字段",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return subject


# ---------- 依赖注入 ----------
def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> models.User:
    """FastAPI 依赖：从 Authorization: Bearer <token> 里取出当前登录用户。

    用法：
        @app.get("/users/me")
        def me(user: Annotated[models.User, Depends(get_current_user)]):
            ...
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    subject = decode_access_token(token)
    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌内容不合法",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
