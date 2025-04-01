import psycopg2
#连接数据库
try:
    conn = psycopg2.connect(
        host="10.32.151.4",
        port="5432",
        database="inspur",
        user="inspur",
        password="lcjg$$9999"
    )
try:
 cursor = conn.cursor()
# 你的查询语句
 query = "SELECT column1, column2 FROM your_table"
# 获取查询结果的字段信息
 cursor.execute(f"SELECT * FROM ({query}) AS sub LIMIT 0")
 columns = cursor.description

# 提取字段名称和数据类型
 create_table_sql = f"CREATE TABLE new_table (\n"
 for col in columns:
    create_table_sql += f"    {col.name} {col.type},\n"
 create_table_sql = create_table_sql[:-2] + "\n);"

 print(create_table_sql)

# 关闭连接
 cursor.close()
 conn.close()