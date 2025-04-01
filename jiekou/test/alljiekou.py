from flask import Flask, request, jsonify
from asyncpg import create_pool
from asgiref.wsgi import WsgiToAsgi
import contextlib

app = Flask(__name__)
API_TOKEN = "9d428f123e65b7c8d1a9e0f356781234"
db_pool = None


class FlaskASGIApp:
    def __init__(self, flask_app):
        self.app = WsgiToAsgi(flask_app)
        self._lifespan = self._build_lifespan()

    @contextlib.asynccontextmanager
    async def _build_lifespan(self):
        global db_pool
        db_pool = await create_pool(
            host="172.31.102.55",
            port=5433,
            user="postgres",
            password="d8cfe3137214759a932014084ac410b9",
            database="postgres",
            min_size=1,
            max_size=10
        )
        yield
        await db_pool.close()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            async with self._lifespan as lifespan:
                await lifespan(scope, receive, send)
        else:
            await self.app(scope, receive, send)


asgi_app = FlaskASGIApp(app)


# 原有查询接口保持不变
@app.route('/query', methods=['POST'])
async def query_pg():
    token = request.headers.get('token', '').replace('Bearer ', '')
    if token != API_TOKEN:
        return jsonify({"error": "token认证失败"}), 401

    data = request.json
    vfname = data.get('vfname')
    orgcode = data.get('orgcode')

    if not vfname or not orgcode:
        return jsonify({"error": "Missing parameters"}), 400

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM dsl.dm_product01_base WHERE vfname = $1 AND orgcode = $2",
            vfname, orgcode
        )
        return jsonify({"data": [dict(row) for row in rows]})


# 新增查询接口（按ID查询）
@app.route('/query_by_id', methods=['POST'])
async def query_by_id():
    # 身份验证（与原接口一致）
    token = request.headers.get('token', '').replace('Bearer ', '')
    if token != API_TOKEN:
        return jsonify({"error": "token认证失败"}), 401

    # 参数校验
    data = request.json
    record_id = data.get('count')

    if not record_id:
        return jsonify({"error": "Missing 'id' parameter"}), 400

    # 类型校验（确保ID是整数）
    try:
        record_id = int(record_id)
    except ValueError:
        return jsonify({"error": "'count' must be an integer"}), 400

    # 数据库查询
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM dsl.dm_product01_base WHERE count = $1",
            record_id
        )

        if not row:
            return jsonify({"error": "Record not found"}), 404

        return jsonify({"data": dict(row)})


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(asgi_app, host='0.0.0.0', port=5000)