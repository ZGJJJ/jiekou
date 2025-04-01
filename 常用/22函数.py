def my_abs(num):
    """

    """
    if num < 0:
        return -num
    else:
        return num
# 在python3.5之后，可以对函数参数和返回值进行类型声明
# shift+table 退格
def new_abs(num: int) -> int:
    if num < 0:
        return -num
    else:
        return num
print(my_abs(-9))
