from functools import wraps
from flask import request, jsonify
from jwt import decode, ExpiredSignatureError, InvalidTokenError
from ..config.settings import JWT_SECRET
from ..core.auth import generate_token
from ..core.database import pg_pool
from datetime import datetime

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