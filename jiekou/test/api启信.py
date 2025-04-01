import time
import hashlib
import requests
import json

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
md5_hash = hashlib.md5(combined.encode('utf-8')).hexdigest()
headers = {
    'Auth-Version': '2.0',
    'appkey': str(appkey),
    'timestamp': str(timestamp),
    'sign': str(md5_hash)

}
body = {
    'name' : '上海建工电子商务有限公司'
}

response = requests.get(url, headers=headers , params=body)
print("Response Status Code:", response.status_code)
print("Response Content:", response.text)





external_data = response.json()
data_dict = external_data.get('data', {})
if isinstance(data_dict, list):
    print("API 返回的是一个列表。")
elif isinstance(data_dict, dict):
    print("API 返回的是一个字典。")
else:
    print("数据类型未知。")
print(data_dict)
