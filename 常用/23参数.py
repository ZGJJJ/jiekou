# 形参
def add(x, y):
    return x + y
result = add(10,20)
print(result)

def add3(*args, init_sum=10):
    print(type(args))
    if args:
        for i in args:
            init_sum += i
    return init_sum


print(add3(3,1,init_sum=90))