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
    # 生成访问令牌
    access_payload = {
        'username': username,  # 用户名，可以用来标识是哪个用户
        'exp': datetime.now(UTC) + timedelta(minutes=30),  # 过期时间：当前时间+60min
        'iat': datetime.now(UTC), # token的创建时间（iat = issued at）
        'type': 'access'
    }
    refresh_payload = {
        'username': username,  # 用户名，可以用来标识是哪个用户
        'exp': datetime.now(UTC) + timedelta(days=90),  # 过期时间：当前时间+90天
        'iat': datetime.now(UTC), # token的创建时间（iat = issued at）
        'type': 'refresh'
    }

    # 使用JWT_SECRET密钥对payload进行加密，生成token
    access_token = encode(access_payload, JWT_SECRET, algorithm='HS256')
    refresh_token = encode(refresh_payload, JWT_SECRET, algorithm='HS256')

    return {
        'access_token' : access_token,
        'refresh_token' : refresh_token
    }

# JWT验证装饰器
def require_jwt(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # 1. 获取访问令牌
        token = request.headers.get('Authorization', '').replace('Bearer ', '')

        # 2. 检查令牌是否存在
        if not token:
            return jsonify({
                "error": "Missing JWT token",
                "error_code": "TOKEN_MISSING"  # 明确的错误代码
            }), 401

        try:
            # 3. 验证访问令牌
            payload = decode(token, JWT_SECRET, algorithms=['HS256'])
            if payload.get('type') != 'access':
                return jsonify({
                    "error": "Invalid token type",
                    "error_code": "TOKEN_INVALID"  # 令牌类型错误
                }), 401

            request.current_user = payload['username']
            return f(*args, **kwargs)

        except ExpiredSignatureError:
            # 4. 处理访问令牌过期
            refresh_token = request.headers.get('Refresh-Token')
            if not refresh_token:
                return jsonify({
                    "error": "Access token expired",
                    "error_code": "ACCESS_TOKEN_EXPIRED",  # 访问令牌过期
                    "message": "Please provide refresh token"
                }), 401

            try:
                # 5. 验证刷新令牌
                refresh_payload = decode(refresh_token, JWT_SECRET, algorithms=['HS256'])
                if refresh_payload.get('type') != 'refresh':
                    return jsonify({
                        "error": "Invalid refresh token type",
                        "error_code": "REFRESH_TOKEN_INVALID"  # 刷新令牌类型错误
                    }), 401

                # 6. 生成新令牌并执行原始请求
                new_tokens = generate_token(refresh_payload['username'])
                response = f(*args, **kwargs)

                # 7. 处理响应格式
                if isinstance(response, tuple):
                    response_data = response[0].get_json()
                    status_code = response[1]
                else:
                    response_data = response.get_json()
                    status_code = 200

                # 8. 添加新令牌到响应中
                response_data['new_tokens'] = {
                    'access_token': new_tokens['access_token'],
                    'refresh_token': new_tokens['refresh_token']
                }

                return jsonify(response_data), status_code

            except ExpiredSignatureError:
                # 9. 处理刷新令牌过期
                return jsonify({
                    "error": "Refresh token expired",
                    "error_code": "REFRESH_TOKEN_EXPIRED",  # 刷新令牌过期
                    "message": "Please login again"
                }), 401

            except InvalidTokenError:
                # 10. 处理刷新令牌无效
                return jsonify({
                    "error": "Invalid refresh token",
                    "error_code": "REFRESH_TOKEN_INVALID",  # 刷新令牌无效
                    "message": "Please login again"
                }), 401

        except InvalidTokenError:
            # 11. 处理访问令牌无效
            return jsonify({
                "error": "Invalid token",
                "error_code": "TOKEN_INVALID",  # 访问令牌无效
                "message": "Please login again"
            }), 401

    return decorated

# API调用统计装饰器
def track_api_usage(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "Missing API key. 缺少API密钥"}), 401

        try:
            #检查额度
            conn = pg_pool.getconn()
            cursor = conn.cursor()

            cursor.execute("""SELECT credit_balance
             FROM api_users
             WHERE api_key = %s""",(api_key,))

            result = cursor.fetchone()
            if not result or result[0] <= 0:
                return jsonify({"error": "额度不足", "credit_balance": result[0] if result else 0}), 403

            # 执行原始API函数
            response = f(*args, **kwargs)

            # 判断API调用是否成功
            if isinstance(response, tuple):
                success = response[1] == 200
                response_data = response[0].get_json()
                status_code = response[1]
            else:
                success = response.status_code == 200
                response_data = response.get_json()
                status_code = 200

                # 获取返回的数据条数并计算所需额度
                data_count = 0
                if success and response_data and 'data' in response_data:
                    if isinstance(response_data['data'], list):
                        data_count = len(response_data['data'])
                    else:
                        data_count = 1

                required_credit = data_count * 100  # 每条数据消耗100额度

                # 检查额度是否足够
                if result[0] < required_credit:
                    return jsonify({
                        "error": "额度不足",
                        "credit_balance": result[0],
                        "required_credit": required_credit,
                        "data_count": data_count
                    }), 403

                # 扣减额度
                if success:
                    cursor.execute("""
                                UPDATE api_users 
                                SET credit_balance = credit_balance - %s,
                                    credit_used = credit_used + %s
                                WHERE api_key = %s
                                RETURNING credit_balance
                            """, (required_credit, required_credit, api_key))

                    new_balance = cursor.fetchone()[0]

                    # 将剩余额度添加到响应中
                    if isinstance(response, tuple):
                        response_data = response[0].get_json()
                        response_data['credit_info'] = {
                            "consumed_credit": required_credit,
                            "remaining_credit": new_balance
                        }
                        response = (jsonify(response_data), status_code)
                    else:
                        response_data = response.get_json()
                        response_data['credit_info'] = {
                            "consumed_credit": required_credit,
                            "remaining_credit": new_balance
                        }
                        response = jsonify(response_data)

            current_time = datetime.now()
            current_date = current_time.date()
            current_hour = current_time.hour
            endpoint = request.endpoint

            # 更新每日统计
            cursor.execute("""
                INSERT INTO api_usage (
                    api_key, endpoint, usage_date, success_count, 
                    fail_count, data_count, year, month, day, hour
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (api_key, endpoint, usage_date)
                DO UPDATE SET 
                    success_count = CASE WHEN %s THEN api_usage.success_count + 1 ELSE api_usage.success_count END,
                    fail_count = CASE WHEN %s THEN api_usage.fail_count + 1 ELSE api_usage.fail_count END,
                    data_count = api_usage.data_count + %s
            """, (
                api_key,
                endpoint,
                current_date,
                1 if success else 0,
                0 if success else 1,
                data_count if success else 0,
                current_time.year,
                current_time.month,
                current_time.day,
                current_hour,
                success,
                not success,
                data_count if success else 0
            ))

            conn.commit()

            # 检查是否有新的令牌需要返回
            if 'new_tokens' in response_data:
                return jsonify(response_data), status_code
            else:
                return response

        except Exception as e:
            return jsonify({"error": str(e)}), 500

        finally:
            cursor.close()
            pg_pool.putconn(conn)

    return decorated

# 用户注册接口
@app.route('/register', methods=['POST'])
def register():
    try:
        # 1. 获取用户提交的数据
        data = request.json  # 获取POST请求中的JSON数据
        username = data.get('username')
        password = data.get('password')
        refresh_token = request.headers.get('Refresh-Token')

        # 2. 验证数据完整性
        if not username or not password:
            if refresh_token:
                # 使用refresh token重新登录
                try:
                    refresh_payload = decode(refresh_token, JWT_SECRET, algorithms=['HS256'])
                    if refresh_payload.get('type') != 'refresh':
                        return jsonify({
                            "error": "Invalid refresh token type",
                            "error_code": "REFRESH_TOKEN_INVALID"
                        }), 401

                    username = refresh_payload.get('username')
                except ExpiredSignatureError:
                    return jsonify({
                        "error": "Refresh token expired",
                        "error_code": "REFRESH_TOKEN_EXPIRED"
                    }), 401
                except InvalidTokenError:
                    return jsonify({
                        "error": "Invalid refresh token",
                        "error_code": "REFRESH_TOKEN_INVALID"
                    }), 401
            else:
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
            # 验证用户凭证
            cursor.execute("""
                SELECT api_key 
                FROM api_users 
                WHERE username = %s AND (password_hash = %s OR %s IS NULL) AND is_active = true
            """, (username, password_hash, password))

            result = cursor.fetchone()
            # 验证失败
            if not result:
                return jsonify({"error": "Invalid credentials"}), 401

            # 5. 生成JWT token
            tokens = generate_token(username)

            # 6. 返回认证信息
            return jsonify({
                "access_token": tokens['access_token'],
                "refresh_token": tokens['refresh_token'],
                "api_key": result[0]
            })

        finally:
            # 7. 清理资源
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
            tokens = generate_token(username)

            # 6. 返回认证信息
            return jsonify({
                "access_token": tokens['access_token'],
                "refresh_token": tokens['refresh_token'],
                "api_key": result[0]
            })

        finally:
            # 6. 清理资源
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API端点
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
@app.route('/usage', methods=['POST'])  # 改为POST请求路由
@require_jwt # 需要JWT token验证
def get_usage():
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "Missing API key"}), 401

        # 从请求体获取查询参数
        data = request.json
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        group_by = data.get('group_by', 'day')  # 可选值: hour, day, month, year
        start_date = data.get('start_date')  # 开始日期 格式: YYYY-MM-DD
        end_date = data.get('end_date')  # 结束日期 格式: YYYY-MM-DD

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        try:
            # 根据不同的分组方式构建查询
            if group_by == 'hour':
                query = """
                           SELECT 
                               endpoint,
                               year,
                               month,
                               day,
                               hour,
                               SUM(success_count) as success_count,
                               SUM(fail_count) as fail_count,
                               SUM(data_count) as total_data_count,
                               SUM(success_count + fail_count) as total_count,
                               usage_date
                           FROM api_usage 
                           WHERE api_key = %s
                       """
                if start_date:
                    query += " AND usage_date >= %s"
                if end_date:
                    query += " AND usage_date <= %s"

                query += """
                           GROUP BY endpoint, year, month, day, hour, usage_date
                           ORDER BY usage_date DESC, hour DESC
                       """

            elif group_by == 'month':
                query = """
                           SELECT 
                               endpoint,
                               year,
                               month,
                               SUM(success_count) as success_count,
                               SUM(fail_count) as fail_count,
                               SUM(data_count) as total_data_count,
                               SUM(success_count + fail_count) as total_count,
                               MIN(usage_date) as month_start,
                               MAX(usage_date) as month_end
                           FROM api_usage 
                           WHERE api_key = %s
                       """
                if start_date:
                    query += " AND usage_date >= %s"
                if end_date:
                    query += " AND usage_date <= %s"

                query += """
                           GROUP BY endpoint, year, month
                           ORDER BY year DESC, month DESC
                       """

            else:  # day 或 year
                if group_by == 'year':
                    select_fields = "year"
                    group_fields = "year"
                else:  # day
                    select_fields = "year, month, day, usage_date"
                    group_fields = "year, month, day, usage_date"

                query = f"""
                           SELECT 
                               endpoint,
                               {select_fields},
                               SUM(success_count) as success_count,
                               SUM(fail_count) as fail_count,
                               SUM(data_count) as total_data_count,
                               SUM(success_count + fail_count) as total_count
                           FROM api_usage 
                           WHERE api_key = %s
                       """
                if start_date:
                    query += " AND usage_date >= %s"
                if end_date:
                    query += " AND usage_date <= %s"

                query += f"""
                           GROUP BY endpoint, {group_fields}
                           ORDER BY {group_fields} DESC
                       """

            # 准备查询参数
            params = [api_key]
            if start_date:
                params.append(start_date)
            if end_date:
                params.append(end_date)

            # 执行查询
            cursor.execute(query, params)

            # 获取列名和结果
            columns = [desc[0] for desc in cursor.description]
            results = []

            for row in cursor.fetchall():
                result_dict = dict(zip(columns, row))

                # 格式化日期
                if 'usage_date' in result_dict:
                    result_dict['usage_date'] = result_dict['usage_date'].strftime('%Y-%m-%d')

                results.append(result_dict)

            # 计算汇总信息
            summary = {
                'total_success': sum(r['success_count'] for r in results),
                'total_fail': sum(r['fail_count'] for r in results),
                'total_data': sum(r['total_data_count'] for r in results),
                'total_calls': sum(r['total_count'] for r in results)
            }

            return jsonify({
                "usage": results,
                "summary": summary,
                "group_by": group_by,
                "start_date": start_date,
                "end_date": end_date,
                "total_records": len(results)
            })

        finally:
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 查询额度接口
@app.route('/credit/balance', methods=['POST'])
@require_jwt
def get_credit_balance():
    try:
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "缺少API密钥"}), 401

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT credit_balance, credit_used 
                FROM api_users 
                WHERE api_key = %s
            """, (api_key,))

            result = cursor.fetchone()
            if not result:
                return jsonify({"error": "无效的API密钥"}), 404

            return jsonify({
                "credit_balance": result[0],
                "credit_used": result[1]
            })

        finally:
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)



