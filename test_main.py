import uuid

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _email() -> str:
    """每次用随机邮箱，避免 sqlite 文件是持久的、重复跑测试会撞「邮箱已注册」"""
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


def _register(email: str, password: str = "secret123") -> dict:
    r = client.post("/users/", json={"email": email, "password": password})
    assert r.status_code == 200
    return r.json()


def _login(email: str, password: str = "secret123") -> str:
    r = client.post("/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# ===== 用户 =====
def test_create_user():
    email = _email()
    body = _register(email)
    assert body["email"] == email
    assert body["is_active"] is True
    assert isinstance(body["id"], int)
    # 密码（无论明文还是哈希）都不该出现在响应里
    assert "password" not in body
    assert "hashed_password" not in body


def test_duplicate_email_rejected():
    email = _email()
    _register(email)
    r = client.post("/users/", json={"email": email, "password": "secret123"})
    assert r.status_code == 400


def test_read_user_404():
    r = client.get("/users/99999999")
    assert r.status_code == 404


def test_read_user_by_id():
    email = _email()
    user = _register(email)
    r = client.get(f"/users/{user['id']}")
    assert r.status_code == 200
    assert r.json()["email"] == email


def test_list_users_and_items():
    assert client.get("/users/").status_code == 200
    assert client.get("/items/").status_code == 200


# ===== 认证 =====
def test_login_returns_token():
    email = _email()
    _register(email)
    token = _login(email)
    assert token
    # JWT 是三段 base64 用 . 连接的
    assert token.count(".") == 2


def test_login_wrong_password_401():
    email = _email()
    _register(email)
    r = client.post("/login", data={"username": email, "password": "wrong-password"})
    assert r.status_code == 401


def test_login_unknown_user_401():
    r = client.post("/login", data={"username": _email(), "password": "secret123"})
    assert r.status_code == 401


def test_users_me_requires_token():
    r = client.get("/users/me")
    assert r.status_code == 401


def test_users_me_with_token():
    email = _email()
    user = _register(email)
    token = _login(email)
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == user["id"]
    assert body["email"] == email


def test_users_me_not_swallowed_by_user_id_route():
    """/users/me 必须排在 /users/{user_id} 前面，否则会被当成 user_id 报 422"""
    email = _email()
    _register(email)
    token = _login(email)
    r = client.get("/users/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == email


def test_users_me_with_garbage_token_401():
    r = client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


# ===== 商品 =====
def test_create_item_for_user():
    email = _email()
    user = _register(email)
    r = client.post(
        f"/users/{user['id']}/items/",
        json={"title": "机械键盘", "description": "cherry 轴体"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "机械键盘"
    assert body["owner_id"] == user["id"]
