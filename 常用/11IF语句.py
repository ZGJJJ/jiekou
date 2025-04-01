"""
年龄判断
1. 可以有用户输入一个年龄
2. 0-18：未成年
3.18-60：打工
4.60以后：老年人
"""
age = int(input ('请输入你的年龄:'))

if 0 <= age < 18:
    print(f'你的年龄是{age},未成年')
elif 18 <= age < 60:
    print(f'你的年龄是{age},打工人')
else:
    print(f'你的年龄是{age},老年人')

# 三目运算
num = int(input('请输入一个整数:'))
# 简单的条件判断
result = f'当前的数字{num}是偶数' if num % 2 == 0 else f'当前的数字{num}是奇数'
print(result)
