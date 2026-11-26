# Pydantic 数据序列化模型
# schemas.py
from pydantic import BaseModel, ConfigDict


# ===== 用户模型 =====
class UserBase(BaseModel):
    email: str


class UserCreate(UserBase):
    password: str          # 创建时需要密码


class UserOut(UserBase):
    id: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)  # 支持 ORM 对象


class Token(BaseModel):
    """登录返回的令牌"""
    access_token: str
    token_type: str = "bearer"


# ===== 商品模型 =====
class ItemBase(BaseModel):
    title: str
    description: str | None = None


class ItemCreate(ItemBase):
    pass


class ItemOut(ItemBase):
    id: int
    owner_id: int

    model_config = ConfigDict(from_attributes=True)