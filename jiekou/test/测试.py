import requests
import json
from datetime import datetime
import time


class APIClient:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.api_key = None
        self.access_token = None
        self.refresh_token = None

    def register(self, username, password):
        """注册新用户"""
        url = f"{self.base_url}/register"
        data = {
            "username": username,
            "password": password
        }

        response = requests.post(url, json=data)
        if response.status_code == 200:
            self.api_key = response.json().get("api_key")
            print(f"注册成功！API Key: {self.api_key}")
            return self.api_key
        else:
            print(f"注册失败: {response.json()}")
            return None

    def login(self, username, password):
        """用户登录"""
        url = f"{self.base_url}/login"
        data = {
            "username": username,
            "password": password
        }

        response = requests.post(url, json=data)
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens.get("access_token")
            self.refresh_token = tokens.get("refresh_token")
            self.api_key = tokens.get("api_key")  # 从登录响应中获取API key
            print("登录成功！")
            print(f"Access Token: {self.access_token}")
            print(f"Refresh Token: {self.refresh_token}")
            print(f"API Key: {self.api_key}")
            return True
        else:
            print(f"登录失败: {response.json()}")
            return False

    def query_company(self, company_name):
        """查询公司信息"""
        if not self.access_token or not self.api_key:
            print("请先登录！")
            print(f"当前状态 - Access Token: {self.access_token}, API Key: {self.api_key}")
            return None

        url = f"{self.base_url}/query"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "company_name": company_name
        }

        print(f"发送请求 - Headers: {headers}")
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"查询失败: {response.json()}")
            return None

    def get_usage_stats(self, group_by="day", start_date=None, end_date=None):
        """获取使用统计"""
        if not self.access_token or not self.api_key:
            print("请先登录！")
            print(f"当前状态 - Access Token: {self.access_token}, API Key: {self.api_key}")
            return None

        if not start_date:
            start_date = "2024-01-01"
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        url = f"{self.base_url}/usage"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        data = {
            "group_by": group_by,
            "start_date": start_date,
            "end_date": end_date
        }

        print(f"发送请求 - Headers: {headers}")
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"获取统计失败: {response.json()}")
            return None

    def test_refresh_token(self, company_name):
        """测试refresh token功能"""
        print("\n=== 开始测试Refresh Token ===")

        # 1. 先尝试正常查询
        print("\n1. 使用原始access token查询")
        result = self.query_company(company_name)
        if result:
            print("原始token查询成功！")

        # 2. 等待access token过期（5分钟）
        print("\n2. 等待access token过期...")
        print("注意：access token有效期为5分钟，这里我们等待6分钟")
        time.sleep(65)  # 等待6分钟

        # 3. 使用过期token尝试查询
        print("\n3. 使用过期token尝试查询")
        result = self.query_company(company_name)
        if result:
            print("警告：过期token仍然可用！")
        else:
            print("过期token已失效，符合预期")

        # 4. 使用refresh token获取新的access token
        print("\n4. 使用refresh token获取新的access token")
        url = f"{self.base_url}/query"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "X-API-Key": self.api_key,
            "Refresh-Token": self.refresh_token,
            "Content-Type": "application/json"
        }
        data = {
            "company_name": company_name
        }

        print(f"发送刷新请求 - Headers: {headers}")
        response = requests.post(url, headers=headers, json=data)
        print(f"刷新响应状态码: {response.status_code}")
        print(f"刷新响应内容: {response.json()}")

        if response.status_code == 200:
            # 从响应中获取新的tokens
            new_tokens = response.json().get("new_tokens")
            if new_tokens:
                self.access_token = new_tokens.get("access_token")
                self.refresh_token = new_tokens.get("refresh_token")
                print("成功获取新的tokens！")
                print(f"新的Access Token: {self.access_token}")
                print(f"新的Refresh Token: {self.refresh_token}")

                # 5. 使用新token测试查询
                print("\n5. 使用新token测试查询")
                result = self.query_company(company_name)
                if result:
                    print("新token查询成功！")
                    return True
            else:
                print("响应中没有新的tokens！")
        elif response.status_code == 401:  # 如果返回未授权错误
            print("Token已过期，尝试使用refresh token重新登录")
            # 尝试使用refresh token重新登录
            login_url = f"{self.base_url}/login"
            login_headers = {
                "X-API-Key": self.api_key,
                "Refresh-Token": self.refresh_token,
                "Content-Type": "application/json"
            }
            login_response = requests.post(login_url, headers=login_headers)
            print(f"重新登录响应: {login_response.json()}")

            if login_response.status_code == 200:
                new_tokens = login_response.json()
                self.access_token = new_tokens.get("access_token")
                self.refresh_token = new_tokens.get("refresh_token")
                print("成功获取新的tokens！")
                print(f"新的Access Token: {self.access_token}")
                print(f"新的Refresh Token: {self.refresh_token}")

                # 5. 使用新token测试查询
                print("\n5. 使用新token测试查询")
                result = self.query_company(company_name)
                if result:
                    print("新token查询成功！")
                    return True
            else:
                print(f"使用refresh token重新登录失败: {login_response.json()}")
        else:
            print(f"刷新token失败: {response.json()}")

        return False

def main():
    # 创建API客户端实例
    client = APIClient()

    # 测试数据
    username = "limy"
    password = "@Bc12345"
    company_name = "上海建工电子商务有限公司"

    try:
        # # 1. 注册
        # print("\n=== 开始注册 ===")
        # client.register(username, password)
        #
        # # 等待1秒
        # time.sleep(1)

        # 2. 登录
        print("\n=== 开始登录 ===")
        if client.login(username, password):
            # 3. 测试refresh token功能
            client.test_refresh_token(company_name)

    except Exception as e:
        print(f"\n发生错误: {str(e)}")


if __name__ == "__main__":
    main()