# # 安装核心依赖（Windows/Linux/macOS通用）
# pip install uvicorn[standard] "asgiref>=3.5" flask[async] asyncpg
import os
from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import pool
import time
import hashlib
import requests
from jwt import encode, decode, ExpiredSignatureError, InvalidTokenError
from datetime import datetime, timedelta
from functools import wraps
import secrets
from datetime import UTC

# 关闭开发服务器警告
os.environ['FLASK_ENV'] = 'development'  # 明确设置为开发环境

# Flask应用初始化
app = Flask(__name__)

# 配置
JWT_SECRET = secrets.token_hex(32)  # 生成随机JWT密钥

# PostgreSQL连接池配置
pg_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host="10.32.151.4",
    port="5432",
    database="inspur",
    user="inspur",
    password="lcjg$$9999"
)

# JWT Token生成函数
def generate_token(username):
    # payload是JWT的数据负载，包含我们想要存储在token中的信息
    payload = {
        'username': username,  # 用户名，可以用来标识是哪个用户
        'exp': datetime.now(UTC) + timedelta(days=1),  # 过期时间：当前时间+1天
        'iat': datetime.now(UTC)  # token的创建时间（iat = issued at）
    }
    # 使用JWT_SECRET密钥对payload进行加密，生成token
    return encode(payload, JWT_SECRET, algorithm='HS256')

# JWT验证装饰器
def require_jwt(f): # f 是被装饰的原始函数（比如query_pg）
    @wraps(f)  # 保留原始函数的元数据
    def decorated(*args, **kwargs):  # 包装函数，处理所有的验证逻辑
        # 1. 从请求头获取token
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        # Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
        # replace('Bearer ', '')是为了删除'Bearer '前缀，只保留token部分

        # 2. 检查token是否存在
        if not token:
            return jsonify({"error": "Missing JWT token"}), 401
        try:
            # 3. 验证token并解码
            payload = decode(token, JWT_SECRET, algorithms=['HS256'])
            # payload 包含之前我们存储的信息,例如：
            # {
            #     'username': 'limy',
            #     'exp': 1710571436,
            #     'iat': 1710485036
            # }
            # 4. 将用户信息存储到请求对象中，供后续使用
            request.current_user = payload['username']
        except ExpiredSignatureError:
            # 5. 处理token过期错误
            return jsonify({"error": "Token has expired"}), 401

        except InvalidTokenError:
            # 6. 处理无效token错误
            return jsonify({"error": "Invalid token"}), 401

        # 7. 验证通过，执行原始函数
        return f(*args, **kwargs)
    return decorated

# API调用统计装饰器
def track_api_usage(f):   # f 是被装饰的原始API函数
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. 验证API key
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "Missing API key"}), 401

        try:
            # 2. 执行原始API函数
            response = f(*args, **kwargs)

            # 3. 判断API调用是否成功
            # response可能是两种形式：
            # a. tuple: (jsonify(data), 200)
            # b. Response对象: response.status_code
            if isinstance(response, tuple):
                success = response[1] == 200   # 如果是元组，检查状态码
            else:
                success = response.status_code == 200  # 如果是Response对象，检查status_code

            # 4. 记录统计信息到数据库
            conn = pg_pool.getconn()
            cursor = conn.cursor()

            try:
                current_date = datetime.now().date()  # 获取当前日期
                endpoint = request.endpoint  # 获取API端点名称

                # 5. 更新统计数据
                cursor.execute("""
                    INSERT INTO api_usage (api_key, endpoint, usage_date, success_count, fail_count)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (api_key, endpoint, usage_date)
                    DO UPDATE SET 
                        success_count = CASE WHEN %s THEN api_usage.success_count + 1 ELSE api_usage.success_count END,
                        fail_count = CASE WHEN %s THEN api_usage.fail_count + 1 ELSE api_usage.fail_count END
                """, (api_key, # API密钥
                      endpoint, # API端点
                      current_date, # 当前日期
                      1 if success else 0, # 成功计数初始值
                      0 if success else 1, # 失败计数初始值
                      success, # 是否成功
                      not success # 是否失败
                      ))

                conn.commit()   # 提交事务
            finally:
                # 6. 清理数据库连接
                cursor.close()
                pg_pool.putconn(conn)

            # 7. 返回原始响应
            return response

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return decorated

# 用户注册接口
@app.route('/register', methods=['POST'])
def register():
    try:
        # 1. 获取用户提交的数据
        data = request.json  # 获取POST请求中的JSON数据
        username = data.get('username')
        password = data.get('password')

        # 2. 验证数据完整性
        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # 3. 生成安全凭证
        # 生成API key和密码哈希
        api_key = secrets.token_hex(32) # 生成64位随机字符的API密钥
        # 对密码进行哈希处理（不存储原始密码）
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # 4. 数据库操作
        conn = pg_pool.getconn()  # 从连接池获取连接
        cursor = conn.cursor()

        try:
            # 插入新用户数据
            cursor.execute("""
                INSERT INTO api_users (username, password_hash, api_key)
                VALUES (%s, %s, %s)
                RETURNING api_key
            """, (username, password_hash, api_key))

            result = cursor.fetchone()  # 获取返回的api_key
            conn.commit()  # 提交事务

            # 5. 返回成功信息
            return jsonify({
                "message": "Registration successful",
                "api_key": result[0]  # 返回api_key给用户
            })
        finally:
            # 6. 清理资源
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 用户登录接口
@app.route('/login', methods=['POST'])
def login():
    try:
        # 1. 获取登录信息
        data = request.json
        username = data.get('username')
        password = data.get('password')

        # 2. 验证数据完整性
        if not username or not password:
            return jsonify({"error": "Missing username or password"}), 400

        # 3. 计算密码哈希
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        # 4. 数据库操作
        try:
            # 验证用户凭证
            cursor.execute("""
                SELECT api_key 
                FROM api_users 
                WHERE username = %s AND password_hash = %s AND is_active = true
            """, (username, password_hash))

            result = cursor.fetchone()
            # 验证失败
            if not result:
                return jsonify({"error": "Invalid credentials"}), 401

            # 5. 生成JWT token
            token = generate_token(username)

            # 6. 返回认证信息
            return jsonify({
                "token": token,
                "api_key": result[0]
            })
        finally:
            # 6. 清理资源
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# 修改现有的API端点
@app.route('/query', methods=['POST'])
@require_jwt
@track_api_usage
def query4_pg():
    try:
        data = request.json
        company_name = data.get('company_name')
        #     vfname = "ABB(中国)有限公司"
        if not company_name:
            return jsonify({"error": "Missing 'company_name' parameter"}), 400

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("SELECT ename,credit_code,score,rating,business_score,undertake_score,stability_score,"
                        "performance_score,risk_score,performance_appraisal,bad_behavior_3y, "
                        "malicious_events_1y,is_blacklist FROM public.dm_internal_evaluation WHERE ename = %s",
                        (company_name,))

        result = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in result]

        return jsonify({"data": data})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            cursor.close()
            pg_pool.putconn(conn)

# 添加使用统计查询接口
@app.route('/usage', methods=['GET'])  # 定义GET请求路由
@require_jwt # 需要JWT token验证
def get_usage():
    try:
        # 1. 验证API key
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "Missing API key"}), 401

        # 2. 数据库连接
        conn = pg_pool.getconn()
        cursor = conn.cursor()

        try:
            # 3. 执行SQL查询
            cursor.execute("""
                SELECT 
                    endpoint,
                    usage_date,
                    success_count,
                    fail_count,
                    (success_count + fail_count) as total_count
                FROM api_usage 
                WHERE api_key = %s 
                ORDER BY usage_date DESC
            """, (api_key,))

            # 4. 处理查询结果
            # 获取列名
            columns = [desc[0] for desc in cursor.description]
            # 将查询结果转换为字典列表
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # 5. 返回JSON结果
            return jsonify({"usage": result})
        finally:
            # 6. 清理资源
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)


