# # 安装核心依赖（Windows/Linux/macOS通用）
# pip install uvicorn[standard] "asgiref>=3.5" flask[async] asyncpg
import os
from flask import Flask, request, jsonify
import psycopg2
from psycopg2 import pool
import time
import hashlib
import requests

# 关闭开发服务器警告
os.environ['FLASK_ENV'] = 'development'  # 明确设置为开发环境,能充分利用调试模式提升效率

# 同步部分：Flask应用的初始化是同步操作
app = Flask(__name__)
API_TOKEN = "9d428f123e65b7c8d1a9e0f356781234"

# 配置 PostgreSQL 连接池（根据实际信息修改）
pg_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    host="10.32.151.4",
    port="5432",
    database="inspur",
    user="inspur",
    password="lcjg$$9999"
)

'''
产品2
上海建工优质供应商名单
'''
@app.route('/query', methods=['POST'])
def query_pg():
    # 同步操作：Token验证
    token = request.headers.get('token', '').replace('Bearer', '')
    if token != API_TOKEN:  # 同步判断
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.json
        vfname = data.get('vfname')
   #     vfname = "ABB(中国)有限公司"
        if not vfname:
            return jsonify({"error": "Missing 'vfname' parameter"}), 400

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM public.dm_product01_base WHERE vfname = %s", (vfname,))
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

'''
产品4
上海建工供应商综合评价(建筑领域启信分)
'''

@app.route('/appraisal', methods=['POST'])
def query4_pg():
    token = request.headers.get('token', '').replace('Bearer', '')
    if token != API_TOKEN:  # 同步判断
        return jsonify({"error": "Unauthorized"}), 401
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
                       "malicious_events_1y,is_blacklist FROM public.dm_internal_evaluation WHERE ename = %s", (company_name,))

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

'''
产品3
上海建工供应商综合评价 内部使用
'''

@app.route('/internalevaluation', methods=['POST'])
def query3_pg():
    token = request.headers.get('token', '').replace('Bearer', '')
    if token != API_TOKEN:  # 同步判断
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.json
        company_name = data.get('company_name')
        #     vfname = "ABB(中国)有限公司"
        if not company_name:
            return jsonify({"error": "Missing 'company_name' parameter"}), 400

        conn = pg_pool.getconn()
        cursor = conn.cursor()

        cursor.execute("SELECT ename,credit_code,rating,score,business_score,undertake_score"
                       ",stability_score,performance_score,risk_score,cooperate_count,business_scope,"
                       "cooperate_amount_avg_3y,cooperate_amount_1y,cooperate_period,"
                       "cooperate_continuity_3y,performance_appraisal,bad_behavior_3y,"
                       "malicious_events_1y,is_blacklist FROM public.dm_internal_evaluation WHERE ename = %s",
                       (company_name,))

        result = cursor.fetchall()

        columns = [desc[0] for desc in cursor.description]
        data = [dict(zip(columns, row)) for row in result]

        # 调用GET请求
        url = "https://api.qixin.com/APIService/creditScore/getCreditScore"
        # 获取当前时间戳（精确到秒）
        timestamp_seconds = time.time()
        # 转换为毫秒级别（保留整数部分）
        timestamp_millis = int(timestamp_seconds * 1000)
        timestamp = str(timestamp_millis)
        appkey = "f4ce0084-c4d2-4a7f-9061-cff619895988"
        secret_key = "51dc9927-71e0-45fe-890d-6bdd904a1581"
        combined = appkey + timestamp + secret_key
        #md5加密
        md5_hash = hashlib.md5(combined.encode('utf-8')).hexdigest()
        #headers参数
        headers = {
            'Auth-Version': '2.0',
            'appkey': str(appkey),
            'timestamp': str(timestamp),
            'sign': str(md5_hash)
        }
        #body参数
        body = {
            'name': company_name
        }
        response = requests.get(url, headers=headers, params=body)
        print("Response Status Code:", response.status_code)

        external_data = response.json()
        # 获取data对象中的score，如果不存在则使用默认值0
        data_dict = external_data.get('data', {})
        score = data_dict.get('score', None)
        row_dict = {"external_score": score/10}
        # 如果data列表中有多个字典，可以考虑合并它们
        if len(data) > 0:
            # 先合并external_score
            combined_data = {**row_dict, **data[0]}
            # 计算总分（数据库分数和API分数加权求和）
            total_score =round((combined_data['external_score'] * 0.2) + (float(combined_data['score'])*0.8),2)
            total_score_dict = {'total_score':total_score}
            print('total_score',total_score)  #终端验证查看，无实际意义
            combined_data2 = {**row_dict,**total_score_dict, **data[0]}
        else:
            combined_data2 = row_dict

        return jsonify({"data": combined_data2})  #返回json格式

    except Exception as e:   #报错捕捉
        return jsonify({"error": str(e)}), 500

    finally:
        if 'conn' in locals():
            cursor.close()
            pg_pool.putconn(conn)

if __name__ == '__main__':
    # 关闭 debug 模式，减少控制台输出
    app.run(host='0.0.0.0', port=5000)  # 注意：debug=False 会禁用自动重载