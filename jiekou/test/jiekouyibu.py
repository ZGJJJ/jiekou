# 安装异步相关依赖（注意flask[async]支持异步视图）
# pip install "asgiref>=3.5" flask[async] asyncpg uvicorn

from flask import Flask, request, jsonify
from asyncpg import create_pool  # 异步PostgreSQL客户端库
from asgiref.wsgi import WsgiToAsgi  # 将WSGI应用转换为ASGI的适配器
import contextlib

# 同步部分：Flask应用的初始化是同步操作
app = Flask(__name__)
API_TOKEN = "9d428f123e65b7c8d1a9e0f356781234"
db_pool = None  # 将保存异步连接池


# 自定义ASGI应用包装器（异步生命周期管理）
class FlaskASGIApp:
    def __init__(self, flask_app):
        # 将WSGI应用转换为ASGI应用
        self.app = WsgiToAsgi(flask_app)  # 同步初始化
        # 构建异步生命周期管理器
        self._lifespan = self._build_lifespan()  # 异步上下文管理器

    @contextlib.asynccontextmanager  # 异步上下文管理器装饰器
    async def _build_lifespan(self):
        # 异步初始化数据库连接池
        global db_pool
        db_pool = await create_pool(  # 异步操作：创建连接池
            host="10.32.151.4",
            port=5432,
            user="inspur",
            password="lcjg$$9999",
            database="inspur",
            min_size=1,
            max_size=10
        )
        yield  # 保持连接池存活
        # 异步清理：关闭连接池
        await db_pool.close()  # 异步操作

    # 异步ASGI调用入口
    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            # 处理ASGI生命周期事件（异步）
            async with self._lifespan as lifespan:
                await lifespan(scope, receive, send)  # 异步执行
        else:
            # 转发请求到ASGI应用
            await self.app(scope, receive, send)  # 异步处理请求


# 将Flask应用包装为ASGI应用（启用异步特性）
asgi_app = FlaskASGIApp(app)  # 同步初始化


# 异步路由处理函数
@app.route('/query', methods=['POST'])
async def query_pg():  # 异步视图函数
    # 同步操作：Token验证
    token = request.headers.get('token', '').replace('Bearer', '')
    if token != API_TOKEN:  # 同步判断
        return jsonify({"error": "Unauthorized"}), 401

    # 同步操作：参数处理
    data = request.json  # 同步获取JSON数据
    company_name = data.get('company_name')
    credit_code = data.get('credit_no')

    if not company_name or not credit_code:  # 同步参数校验
        return jsonify({"error": "Missing parameters"}), 400

    # 异步数据库操作
    async with db_pool.acquire() as conn:  # 异步获取连接
        # 异步执行查询
        rows = await conn.fetch(  # 异步等待查询结果
            "SELECT * FROM public.dm_cooperation WHERE company_name = $1 AND credit_code = $2",
            company_name, credit_code
        )
        # 同步操作：结果转换（Row转dict）
        return jsonify({"data": [dict(row) for row in rows]})  # 同步序列化



if __name__ == '__main__':
    import uvicorn
    # 使用uvicorn运行ASGI应用（支持异步）
    uvicorn.run(asgi_app, host='0.0.0.0', port=5000)  # 启动异步服务器