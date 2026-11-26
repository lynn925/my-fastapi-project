from fastapi import FastAPI, Path, Query, Header, Cookie,HTTPException,status,UploadFile,File # 导入FastAPI类和参数类型
from pydantic import BaseModel,Field, ConfigDict, EmailStr # 模型类校验，模型配置,邮箱校验
from typing import Annotated # 类型标注工具
from fastapi.responses import RedirectResponse, JSONResponse #重定向 自定义响应头
from fastapi import Depends # 函数依赖注入
from fastapi import Form #表单数据
import asyncio #异步操作


# app = FastAPI() # 创建FastAPI应用实例
app = FastAPI(
    title="lynn 的API",
    description= "这是一个示例，展示文档自定义",
    version="1.0.0",
    terms_of_service="http://example.com/terms/", # 服务条款url
    contact={ # 联系信息
        "name":"开发者lynn",
        "url":"http://example.com/",
        "email":"lynn@example.com" # 必须是合法邮箱，否则 /openapi.json 会 500
    },
    license_info={ # 许可证信息
        "name":"MIT",
        "url":"https://opensource.org/licenses/MIT"
    },
    # docs_url=None, #禁用访问文档Swagger UI
    # redoc_url=None, #禁用访问文档ReDoc

)

# 认证路由（JWT + bcrypt），见 auth.py
from auth import router as auth_router, log_unhandled_exception
app.include_router(auth_router)
app.add_exception_handler(Exception, log_unhandled_exception)

@app.get("/") # 定义根路径的GET请求处理函数
async def read_root(): 
    """根路径，返回欢迎信息"""
    return {"Hello": "World"}
@app.get("/items/{item_id:int}") # :int 转换器：只匹配数字，否则 /items/dep 会被这条路由抢先匹配导致 422
async def read_item(item_id: int, q: str = None,user_agent:str=Header(None),session_token:str=Cookie(None)):
    """获取指定ID的项目"""
    return {"item_id": item_id, "q": q, "user_agent":user_agent,"session_token":session_token}

#重定向
# 代码在浏览器访问 http://127.0.0.1:8000/redirect/ 会自动跳转到 http://127.0.0.1:8000/items/ 页面：
@app.get("/redirect")
def redirect():
    return RedirectResponse(url="/items/")

# 定义请求体数据模型 基础模型
class Item(BaseModel):
    name:str  # 必填：名称
    description:str | None=None # 可选：描述
    price: float # 必填
    tax: float | None=None
    email:EmailStr #必填 自动校验邮箱格式
    # pydantic v2的配置方式
    model_config=ConfigDict(
        json_schema_extra={ # 在API文档中显示示例
            "examples":[
                {
                    "name":"Foo",
                    "price":35.4,
                    "email":"lynn@example.com",
                    "password":"123456"
                }
            ]
        }
    )
# 模型继承
# 创建用户时的输入模型（包含密码）
class UserCreate(Item):
    password:str #必填

# 返回用户信息时的输出模型（不包含密码）
class UserOut(Item):
    id:int
@app.post("/items/",tags=['新增'],response_model=UserOut) #新增
async def create_item(user:UserCreate):
    # print(item.name)
   # 序列化为字典
#    item_dict=item.model_dump()
#    print(item_dict)
   #序列化为JSON字符串
    # item_json=item.model_dump_json()
    # print(item_json)
    # return item_json

    # 函数接收 UserCreate（含密码），但响应使用UserOut（不含密码）
    # 这样密码就不会出现在响应中
    item_dict=user.model_dump(exclude={"password"})
    item_dict["id"] = 1  # UserOut 里的 id 是必填字段，Item 中没有，需要手动补上
    return item_dict
   

@app.put("/items_put/{item_id}",tags=["商品管理"]) # 分组标签) #更新
async def update_item(item_id:int,item:Item):
    if item_id == 42:
        raise HTTPException(status_code=404,detail="Item not detail")
    return{"item_id":item_id,"item_name":item.name}

@app.get(
    "/itemsRead/{item_id}",
    summary="获取商品信息",#简短摘要
    description="根据商品 ID 获取商品的详细信息", #详细描述
    response_description="商品信息对象", #响应描述
    tags=["商品管理"] # 分组标签
)
#Path用于路径中的参数校验
# Annotated[int, Path(gt=0)]        # 大于 0
# Annotated[int, Path(ge=1)]        # 大于等于 1
# Annotated[int, Path(le=100)]      # 小于等于 100
# Annotated[int, Path(description="商品 ID")]
#Quer用于常用查询参数校验
#q: Annotated[str | None, Query(
    #title="查询字符串",           # 参数标题
    #min_length=2,          # 最小长度 2 个字符
    #max_length=20,         # 最大长度 20 个字符
    #pattern="^[a-zA-Z]+$",  # 正则约束：只允许英文字母（不含数字和符号）
    #description="搜索关键词"  # 参数描述，会显示在 Swagger 文档中
    #alias="item-query",    # URL 中的参数名别名
    #deprecated=True,       # 标记为已弃用
#)] = None                 # 默认值为 None，表示该查询参数可选
async def read_item( 
    item_id:Annotated[int,Path(ge=1,description="商品ID")],
    q:Annotated[str|None,Query(description="搜索关键词")] = None
    # q 可以在 URL 中出现多次，值会被收集为列表
    # q: Annotated[list[str] | None, Query()] = None,
    # http://127.0.0.1:8000/items/?q=foo&q=bar
    # {"q": ["foo", "bar"]}

):
    content={'item_id':item_id}
    headers = {"X-Custom-Header":"custom-header-value"}
    return JSONResponse(content=content,headers=headers)
    # return {"item_id":item_id,"q":q}

# 参数校验总结
# 查询参数用Annotated+Query   
# q: Annotated[str | None, Query(
#         title="查询字符串",           # 参数标题
#         description="用于筛选商品的查询字符串",  # 参数描述
#         min_length=3,
#         max_length=50,
#         alias="item-query",    # URL 中的参数名别名
#         deprecated=True,       # 标记为已弃用
#     )] = None,
# 查询参数校验的核心要点：
# 使用 Annotated + Query 声明校验规则（推荐方式）
# 字符串校验：min_length、max_length、pattern
# 没有默认值 = 必填参数，有默认值 = 可选参数
# alias 用于 URL 中使用非 Python 变量名的参数名
# deprecated=True 标记过时的参数
# 使用 list[str] 接收多个相同名称的查询参数

# 路径参数用Annotated+Path
# item_id: Annotated[int, Path(title="商品ID", ge=1, le=1000)],
# q: Annotated[str | None, Query(max_length=50)] = None,
# 路径参数数值校验的核心要点：
# 使用 Annotated + Path 声明路径参数的校验规则
# 数值校验：gt（大于）、ge（大于等于）、lt（小于）、le（小于等于）
# Path 和 Query 共享相同的校验参数，包括字符串校验（min_length 等）和元数据（title、description 等）
# 路径参数始终是必填的，无论是否声明默认值

# 请求体参数校验 用pydantic的BaseModel，Field
class Item(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="商品名称")  # 必填，1-100字符
    description: str | None = Field(default=None, max_length=300, description="商品描述")  # 可选
    price: float = Field(gt=0, description="商品价格")  # 必填，必须大于 0
    tax: float | None = Field(default=None, ge=0, description="税费")  # 可选，>= 0
@app.post("/itemsceshi/")
async def create_item(item: Item):
    return item
# 小结
# 使用 Pydantic 的 Field 为模型字段添加校验和元数据
# list[str]、set[str] 等集合类型可以声明列表/集合字段
# 模型可以嵌套使用，支持任意深度的 JSON 结构
# HttpUrl 等特殊类型自动校验格式
# 纯列表和任意字典也可以作为请求体类型


# FastAPI 官方文档专门讲过这个坑：路径参数路由要放在最后注册，否则会吃掉同前缀下的静态路径。

# 依赖注入

#函数依赖
# 1.定义依赖函数
def common_parameters(q:str|None=None,skip:int=0,limit:int=100):
    return {"q":q,"skip":skip,"limit":limit}
# 2.在路由中使用依赖函数
@app.get("/items/dep")
async def read_items_dep(commons:dict=Depends(common_parameters)):
    #commons接收依赖函数的返回值
    return commons
@app.get("/user/dep")
async def read_uesr_dep(commons:dict=Depends(common_parameters)):
    # 多个路由可以复用同一个依赖函数
    return commons
# 类依赖 Annotated

# 声明类依赖
class CommonQueryParams:
    def __init__(self,q:str|None=None,skip:int=0,limit:int=100):
        self.q=q
        self.skip = skip
        self.limit = limit
# 作为类依赖注入
# 当 Depends() 不传入参数时，FastAPI 会自动使用参数的类型注解（CommonQueryParams）作为依赖。
@app.get('/itemsClass/')
async def read_class(commons:Annotated[CommonQueryParams,Depends()]):
    return {"q":commons.q, "skip": commons.skip, "limit": commons.limit,"commons":commons}

#子依赖
# 依赖函数
def query_extractor(q: str | None = None):
    return q
# 子依赖：依赖 query_extractor
def query_checker(q: str = Depends(query_extractor)):
    if q == "admin":
        # 子依赖可以进行校验
        return q + " (checked)"
    return q
# 路由使用子依赖
@app.get("/itemschild/")
async def read_items(q: str = Depends(query_checker)):
    return {"q": q}
# 执行流程：query_extractor -> query_checker -> 路由函数

# 在装饰器中使用依赖
# 有时你只需要依赖的副作用（如权限校验），不需要其返回值。可以在装饰器的 dependencies 参数中声明：
# 依赖：校验 API Key
async def verify_api_key(x_api_key: str = Header()):
    if x_api_key != "secret-keyXXX":
        raise HTTPException(status_code=400, detail="X-API-Key invalid")
# 在装饰器中使用依赖，不需要返回值
@app.get("/items/", dependencies=[Depends(verify_api_key)])
async def read_items():
    return [{"item": "Foo"}]
# 对整个路由组使用依赖
@app.get("/users/", dependencies=[Depends(verify_api_key)])
async def read_users():
    return [{"user": "Bar"}]

#全局依赖
# 可以在 FastAPI 实例上声明全局依赖，对所有路由生效：
# 全局依赖：所有路由都需要通过 token 校验
# app = FastAPI(dependencies=[Depends(verify_api_key)])

# 使用 yield 的依赖
# 使用 yield 的依赖：请求前创建连接，请求后关闭连接
def get_db():
    db = "database_connection"  # 模拟创建数据库连接
    try:
        yield db  # 请求处理期间提供数据库连接
    finally:
        print("关闭数据库连接")  # 请求完成后清理资源
@app.get("/itemsYield/")
async def read_items(db: str = Depends(get_db)):
    return {"db": db}
# 请求到达时，执行 yield 之前的代码，创建数据库连接
# yield 将连接传递给路由函数
# 路由函数执行完毕后，执行 finally 块中的清理代码
# yield 依赖非常适合管理数据库连接、文件句柄等需要清理的资源。无论路由函数是否抛出异常，清理代码都会执行。

#表单数据 form
# 使用 Form 接收 HTML 表单提交的数据
# 表单数据不是 JSON，不能与 BaseModel 请求体混用
# Form() 声明必填字段，Form(None) 声明可选字段
# 需要安装 python-multipart 包
@app.post("/login/")
async def login(
    username:str=Form(),
    password:str=Form(),
    des:str|None=Form(None), # 可选，默认none
    pri:float=Form(...,gt=0) # 必填 必须大于0
):
    return {"username":username,"des":des,"pri":pri}

#异步操作
# 异步路径操作（推荐）
@app.get('/sync')
async def saync_end():
      # 异步操作不会阻塞其他请求
    await asyncio.sleep(2)
    return{"message":"异步响应"}

# 异步数据库操作示例  
# @app.get("/async/{user_id}")
# async def get_user(user_id:int):
#     #database是数据库连接，现在是假的
#     user=await database.fetch_one(
#         "SELECT * FROM user WHERE id=:user_id",
#         {"user_id":user_id}
#     )
#     return user

# 响应状态码
@app.get("/status/",status_code=status.HTTP_200_OK)
async def get_status():
    return {"message": "请求成功"}
@app.post("/status/",status_code=status.HTTP_201_CREATED)
async def create_status():
    return {"message": "资源已创建"}
@app.delete("/status/",status_code=status.HTTP_204_NO_CONTENT)
async def delete_status():
    return {"message": "资源已删除"}

# 文件上传 UploadFile
@app.post("/uploadfile/",tags=["文件上传"])
async def upload_file(file:UploadFile | None=None):
    if not file:
        return {"message": "没有文件被上传"}
    return {
        "filename":file.filename,
        "content_type":file.content_type,
        "size":len(await file.read()),
        "size2":file.size
    }
# 多文件上传
@app.post("/uploadfiles/",tags=["文件上传"])
async def upload_files(files:list[UploadFile]=File(...)):
    return [{"filename":file.filename,"content_type":file.content_type,"size":len(await file.read())} for file in files]

#表单和文件混合
@app.post("/uploadfileform/",tags=["文件上传"])
async def upload_file_form(file:UploadFile=File(...),description:str=Form(...)):
    return {
        "filename":file.filename,
        "content_type":file.content_type,
        "size":len(await file.read()),
        "description":description
    }
import shutil
# 保存上传的文件
@app.post("/savefile/",tags=["文件上传"])
async def save_file(file:UploadFile=File(...)):
    # 保存文件到本地
    with open(f"uploaded_{file.filename}", "wb") as f:
        # f.write(await file.read())
        shutil.copyfileobj(file.file, f)
    return {"message": f"文件 {file.filename} 已保存"}

# 使用 File 接收文件内容 File 直接将文件内容读取为 bytes，适合小文件
@app.post("/file/",tags=["文件上传"])
async def upload_file(file:bytes=File()):
    return {
        "file_size":len(file)
    }
# 请求头header 和cookie

@app.get("/headers/",tags=["请求头和Cookie"])
async def read_item(user_agent:Annotated[str|None,Header()]=None):
    return {"User-Agent":user_agent}
# 请求头会自动转换
@app.get("/headersToken/",tags=["请求头和Cookie"])
async def read_cookie(
     # Python 变量名用下划线，FastAPI 自动转换为 X-Token 请求头 "X-Token": "wwwwww"
    x_token:Annotated[str|None,Header()]=None,
     # 接收多个 X-Token 请求头 "X-Token": ["stringsssss,stringssswqqw"]
    # x_token: Annotated[list[str] | None, Header()] = None,
):
    return {"X-Token":x_token}

# Cookie
@app.get("/cookies/",tags=["请求头和Cookie"])
async def read_cookie(
    session_token:Annotated[str|None,Cookie()]=None
):
    return {"session_token":session_token}
#请求头与 Cookie 同时使用
@app.get("/cookies_headers/",tags=["请求头和Cookie"])
async def read_items(
    user_agent: Annotated[str | None, Header()] = None,
    session_token: Annotated[str | None, Cookie()] = None,
    ads_id: Annotated[str | None, Cookie()] = None,
):
    return {
        "User-Agent": user_agent,
        "Session-Token": session_token,
        "Ads-ID": ads_id,
    }
#错误校验 HTTPException 
@app.get("/error/{item_id}",tags=["错误处理"])
async def read_item(item_id:int):
    if item_id==3:
        raise HTTPException(status_code=418,detail="This is a teapot",headers={"X-Error":"There goes my error"})
    return {"item_id":item_id}

import time
# 中间件
@app.middleware("http")
async def add_process_time_header(request,call_next):
    # 在请求处理前执行的逻辑
    start_time=time.time()
    #调用下一个中间件或者路由处理函数
    response=await call_next(request)
    # 在请求处理后执行的逻辑
    process_time=time.time()-start_time
    response.headers["X-Process-Time"]=str(process_time)
    return response
#路由函数
@app.get("/middleware/",tags=["中间件"])
async def read_items():
    return {"message":"Hello, Middleware!"}
# 请求日志中间件
@app.middleware("http")
async def log_request(request, call_next):
    # 在请求处理前记录日志
    print(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    # 在请求处理后记录日志
    print(f"Response status code: {response.status_code}")
    return response
@app.get("/log/",tags=["中间件"])
async def log_items():
    return {"message": "Hello, Log Middleware!"}
# 使用 Starlette 内置中间件
# HTTPSRedirectMiddleware	强制将 HTTP 请求重定向为 HTTPS
# TrustedHostMiddleware	限制允许访问的主机名
# GZipMiddleware	自动压缩响应内容
# CORSMiddleware	处理跨域请求（下一章详细介绍）
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware # 导入 HTTPS 重定向中间件
from starlette.middleware.cors import CORSMiddleware # 导入 CORS 中间件
# 强制 HTTPS 重定向
# app.add_middleware(HTTPSRedirectMiddleware)

# CORS 跨域
# 使用 Starlette 的 CORSMiddleware 来处理跨域：
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,  # 允许发送 Cookie
    allow_methods=["*"],  # 允许所有 HTTP 方法
    allow_headers=["*"],  # 允许所有请求头
)
# 生产环境：只允许特定域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://example.com",           # 生产前端域名
        "https://www.example.com",       # 带 www 的域名
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    max_age=600,                  # 预检请求缓存 10 分钟
)

#测试
from fastapi.testclient import TestClient
client = TestClient(app)
#测试函数
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World22222"}