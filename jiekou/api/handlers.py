from flask import request, jsonify
from ..core.database import pg_pool
from datetime import datetime


def handle_query():
    """处理查询请求的业务逻辑"""
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


def handle_usage():
    """处理使用统计查询的业务逻辑"""
    try:
        # 1. 验证API密钥
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({"error": "缺少API密钥"}), 401

        # 2. 获取请求参数
        data = request.json
        if not data:
            return jsonify({"error": "Missing request body"}), 400

        group_by = data.get('group_by', 'day')  # 默认按天分组
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        # 3. 验证分组参数
        valid_group_by = ['hour', 'day', 'month', 'year']
        if group_by not in valid_group_by:
            return jsonify({
                "error": f"Invalid group_by parameter. Must be one of: {', '.join(valid_group_by)}"
            }), 400

        # 4. 构建查询
        query = _build_usage_query(group_by, start_date, end_date)

        # 5. 准备查询参数
        params = [api_key]
        if start_date:
            try:
                datetime.strptime(start_date, '%Y-%m-%d')
                params.append(start_date)
            except ValueError:
                return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

        if end_date:
            try:
                datetime.strptime(end_date, '%Y-%m-%d')
                params.append(end_date)
            except ValueError:
                return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

        # 6. 执行数据库查询
        conn = pg_pool.getconn()
        cursor = conn.cursor()

        try:
            # 执行查询
            cursor.execute(query, params)

            # 获取列名和结果
            columns = [desc[0] for desc in cursor.description]
            results = []

            # 7. 处理查询结果
            for row in cursor.fetchall():
                result_dict = dict(zip(columns, row))
                # 格式化日期字段
                for date_field in ['usage_date', 'month_start', 'month_end']:
                    if date_field in result_dict and result_dict[date_field]:
                        result_dict[date_field] = result_dict[date_field].strftime('%Y-%m-%d')
                results.append(result_dict)

            # 8. 计算汇总信息
            summary = {
                'total_success': sum(r['success_count'] for r in results),
                'total_fail': sum(r['fail_count'] for r in results),
                'total_data': sum(r['total_data_count'] for r in results),
                'total_calls': sum(r['total_count'] for r in results)
            }

            # 9. 返回结果
            return jsonify({
                "usage": results,
                "summary": summary,
                "group_by": group_by,
                "start_date": start_date,
                "end_date": end_date,
                "total_records": len(results),
                "params": {  # 添加查询参数信息
                    "group_by": group_by,
                    "start_date": start_date,
                    "end_date": end_date
                }
            })

        finally:
            # 10. 清理资源
            cursor.close()
            pg_pool.putconn(conn)

    except Exception as e:
        # 11. 错误处理
        return jsonify({
            "error": str(e),
            "error_type": type(e).__name__
        }), 500


def handle_credit_balance():
    """处理额度查询的业务逻辑"""
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


def _build_usage_query(group_by, start_date=None, end_date=None):
    """构建使用统计查询SQL

    Args:
        group_by (str): 分组方式 ('hour', 'day', 'month', 'year')
        start_date (str, optional): 开始日期
        end_date (str, optional): 结束日期
    """
    if group_by == 'hour':
        return """
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
            AND usage_date >= COALESCE(%s, usage_date)
            AND usage_date <= COALESCE(%s, usage_date)
            GROUP BY endpoint, year, month, day, hour, usage_date
            ORDER BY usage_date DESC, hour DESC
        """
    # 其他group_by选项的查询语句...（与原代码相同）

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
        return query

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
        return query

