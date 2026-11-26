# my-fastapi-project

一个 FastAPI + SQLAlchemy 的练手项目，包含用户/商品 CRUD 与 JWT 认证。

## 功能

- **用户**：注册（bcrypt 哈希）、列表、详情、当前登录用户
- **认证**：`POST /login` 走 OAuth2 表单，换取 JWT（HS256），后续请求用 `Authorization: Bearer <token>`
- **商品**：创建、列表
- 统一异常处理，未捕获异常写入 `server_error.log`

## 文件结构

| 文件 | 作用 |
| --- | --- |
| `main.py` | FastAPI 应用与全部路由 |
| `database.py` | engine / Base / `get_db` 依赖 |
| `models.py` | SQLAlchemy ORM 模型（User、Item） |
| `schemas.py` | Pydantic 请求/响应模型 |
| `crud.py` | 数据库操作 |
| `auth.py` | 密码哈希、JWT 签发与校验、`get_current_user` 依赖 |
| `test_main.py` | pytest 测试 |
| `main1.py` | 学习过程中的 API 特性示例（非主应用） |
| `work/学习文档.md` | 学习笔记 |

分层是为了避免循环 import：`database` → `models` → `auth` → `crud` → `main`。

## 运行

```bash
pip install -r requirements.txt

export SECRET_KEY="换成你自己的密钥"        # 生产必须注入
export ACCESS_TOKEN_EXPIRE_MINUTES=30        # 可选，默认 30

uvicorn main:app --reload --port 8002
```

首次启动会自动建表（SQLite 文件 `sql_app.db`，由 `Base.metadata.create_all` 创建）。
注意数据库用的是相对路径，**必须在项目目录下启动**，否则 db 文件会落到别处。

打开 http://127.0.0.1:8002/docs 使用 Swagger UI。

## 测试

```bash
pytest
```

## 接口速查

| 方法 | 路径 | 认证 | 说明 |
| --- | --- | --- | --- |
| POST | `/users/` | 否 | 注册，body `{email, password}` |
| GET | `/users/` | 否 | 用户列表 |
| GET | `/users/me` | 是 | 当前登录用户 |
| GET | `/users/{user_id}` | 否 | 用户详情 |
| POST | `/login` | 否 | 表单 `username`(邮箱) + `password` |
| POST | `/users/{user_id}/items/` | 否 | 创建商品 |
| GET | `/items/` | 否 | 商品列表 |

## 已知实现细节

- bcrypt 5.0 起不再静默截断超 72 字节的密码，`auth.py` 里注册和校验统一按字节截断到 72，两边规则一致。
- 没有用 passlib：passlib 1.7.4 加载后端时的 wraparound 自检会与 bcrypt 5.0 冲突并报错。如需继续用 passlib，请 `pip install "bcrypt<5"`。
- `SECRET_KEY` 有开发用的默认值兜底，正式环境务必用环境变量覆盖。
