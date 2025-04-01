#第一种

my_name ='张三'
my_age = 22
my_city ='SH'

print('我的名字是%s' % my_name)

print('我的名字是%s,我的年龄是%d' % (my_name,my_age))
print('我的名字是%s,我的年龄是%d,我所在的城市是%s' % (my_name,my_age,my_city))

#特殊格式化
money =8923
num =1.71

print('我的金额是：%5d' % money)
print('我的金额是：%d' % money)

#精确到小数点后一位：四舍五入
print('%.1f' % num)

num02=66.125
print('%.2f' % num02)

#精确的四舍五入
from decimal import Decimal

print(Decimal(str(num02)).quantize(Decimal('0.00'), rounding='ROUND_HALF_UP'))

#第二种：格式化
print(f'我的名字是{my_name},我的年龄是{my_age+2},我所在的城市是{my_city}' )
