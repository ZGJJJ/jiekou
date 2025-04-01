import pandas as pd

# 读取 Excel 文件
df = pd.read_excel("202402二级单位分表.xlsx")

# 将所有文本内容转换为数值（如果可能）
for col in df.columns:
    try:
        # 尝试将列转换为数值类型
        df[col] = pd.to_numeric(df[col], errors='coerce')
    except Exception as e:
        print(f"无法处理列 {col}: {e}")

# 保存为新的 Excel 文件（所有内容均为数值）
df.to_excel("202402二级单位分表_converted.xlsx", index=False)