import numpy as np

# 数据
year = [2019, 2020, 2021, 2022,2023,2024]
revenue = [1065,1277,1350,1222,1712,1456]

# 拟合线性回归模型
coefficients = np.polyfit(year, revenue, 1)
predicted_2025 = coefficients[1] + coefficients[0] * 2025

print(f"预测的2025年交易额为：{predicted_2025}万元")



from statsmodels.tsa.holtwinters import SimpleExpSmoothing
# 数据
revenue =[1065,1277,1350,1222,1712,1456]
# 拟合指数平滑模型
model = SimpleExpSmoothing(revenue)
fitted_model = model.fit(smoothing_level=0.5)
# 预测2025年
predicted_2025 = fitted_model.forecast(1)[0]
print(f"预测的2025年交易额为：{predicted_2025}万元")