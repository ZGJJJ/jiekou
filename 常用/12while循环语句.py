# 计算1-100的所有奇数的和
my_sum = 0 # 定义一个结果
n = 1
while 1 <= n <= 100 :
    if n % 2 != 0:
     my_sum += n
    n += 1
print(f'结果是:{my_sum}')

# 输出99乘法表
# 思考99乘法表:有9行

i = 1
while i <= 9: # 代表行数
    j = 1
    while j <= i :
        # 该行所有算式输出
       print(f'{j}*{i}={j*i}', end='\t')
       j += 1
    i += 1
    print('\n')
