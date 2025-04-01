lst = [12, 'ab' , 3.14 , [1,2]]
# 做修改
lst[1] = 'abc'
print(lst)

print(lst.index(12))
print(lst.count(12))
print(len(lst))

#添加数据
lst.append('hello')
lst.extend('world')
lst.insert(0,100)
print(lst)
#删除操作
# lst.pop(2)
# del lst[2]
lst.remove('abc') #remove只删第一个

print(lst)
#逆序
print(lst[::-1])
lst.reverse()

lst2 = [4,9,98,34,2,12]
lst2.sort(reverse=True)
print(lst2)

for i in lst:
    print(i)