# main.py
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import models, schemas, crud
from auth import create_access_token, get_current_user, verify_password
from database import engine, SessionLocal, Base, get_db

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="用户与商品 API", version="1.0.0")


# ===== 认证 =====
@app.post("/login", response_model=schemas.Token, tags=["认证"])
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    """登录换取 JWT 令牌。

    注意：用的是 OAuth2 标准表单，字段名固定叫 username / password，
    我们这里拿 username 当邮箱用，所以表单里填的是邮箱地址。

    注册请用 POST /users/（那里会把密码用 bcrypt 哈希后存进 users 表）。
    """
    user = crud.get_user_by_email(db, email=form.username)
    if not user or not verify_password(form.password, user.hashed_password):
        # 用户不存在和密码错误返回同样的信息，避免暴露「该邮箱是否注册过」
        raise HTTPException(
            status_code=401,
            detail="邮箱或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # sub 放用户 id，登录后所有请求都靠它定位用户
    return schemas.Token(access_token=create_access_token(subject=str(user.id)))


# ===== 用户路由 =====
@app.post("/users/", response_model=schemas.UserOut, tags=["用户"])
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    # 检查邮箱是否已存在
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="邮箱已注册")
    return crud.create_user(db=db, user=user)


@app.get("/users/", response_model=list[schemas.UserOut], tags=["用户"])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


# ⚠️ 这个路由必须注册在 /users/{user_id} 之前！
# 否则请求 /users/me 会被 /users/{user_id} 抢先匹配，
# 而 user_id 要求是 int，FastAPI 会返回 422 而不是走我们的逻辑。
@app.get("/users/me", response_model=schemas.UserOut, tags=["用户"])
def read_current_user(
    current_user: Annotated[models.User, Depends(get_current_user)],
):
    """需要登录才能访问，返回当前登录用户"""
    return current_user


@app.get("/users/{user_id}", response_model=schemas.UserOut, tags=["用户"])
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return db_user


# ===== 商品路由 =====
@app.post("/users/{user_id}/items/", response_model=schemas.ItemOut, tags=["商品"])
def create_item_for_user(
    user_id: int,
    item: schemas.ItemCreate,
    db: Session = Depends(get_db),
):
    return crud.create_item(db=db, item=item, user_id=user_id)


@app.get("/items/", response_model=list[schemas.ItemOut], tags=["商品"])
def read_items(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    items = crud.get_items(db, skip=skip, limit=limit)
    return items


# ===== 统一异常处理：记到文件，不把内部细节暴露给客户端 =====
import traceback

ERROR_LOG = "server_error.log"


@app.exception_handler(Exception)
async def log_unhandled_exception(request, exc):
    """未捕获异常统一记到 server_error.log，方便本地排查。

    生产环境请换成标准 logging 输出到 stderr/日志系统，
    响应里只给一句通用错误，不要把 traceback 泄露给客户端。
    """
    tb = traceback.format_exc()
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(f"{request.method} {request.url}\n{tb}\n" + "=" * 60 + "\n")
    except Exception:
        pass
    return JSONResponse(status_code=500, content={"detail": "服务器内部错误，请查看 server_error.log"})
