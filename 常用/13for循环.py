# 计算1-100的所有奇数的和
my_sum = 0 # 定义一个结果

# for n in range(1, 100, 2):
#     my_sum += n
# print(f'结果是:{my_sum}')

# 第二种写法

# for n in range(100):
#     if n % 2 != 0:
#         my_sum += n
# print(f'结果是:{my_sum}')

# 第三种写法
# n = 0
# while True:
#     n += 1
#     if n > 100: # 超出循环范围,则退出
#         break
#     if n % 2 != 0:
#         my_sum += n
# print(f'结果是:{my_sum}')

# # 第四种写法
# for n in range (100):
#     if n % 2 == 0:  # 当前的n为偶数,不做计算,退出当次循环，继续下一个数字
#         continue
#     my_sum += n
# print(f'结果是:{my_sum}')

for i in range(1,10):
    for j in range(1,i):
        print(f'{j}*{i}={i*j}',end='\t')
    print()