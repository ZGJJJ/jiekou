s1 = 'hello'
s7 = '我是\"湖南\"人'

# print(s1[1])
# print(s7[0])
# print(s7[1])
# print(s7[2])

s = 'abcefghijk'
# 截取字符串：切片 包头不包尾
print(s[2:6:1])
print(s[2:6])
print(s[-8:-4])
print(s[:4])
print(s[5:])

# 字符串倒序
print(s[::-1])

# 字符串的函数
ss = 'hellopythonpyworld'

# 除了查找目标字符串，还可以做判断
print(ss.rfind('py'))
print(ss.find('h'))

# 字符串切割
sss = 'I am a student'
print(sss.split(' ')) # 切割:分隔符不会在结果中出现
print(sss.partition('am')) # 区分：分隔符单独一个一个区

# 字符串替换
print(sss.replace('student', 'worker'))
