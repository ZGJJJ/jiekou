import random #导入random模块
print("-" * 50)
print("猜数游戏")
print("-" * 50)

#定义一个记录游戏次数变量
n = 0
while True :
    order = input('请输入是否开始游戏:')
    if order == 'yes' or order == 'y': #用户想玩游戏
        number = random.randint(1,10)  #系统生成随机数
        n += 1
        for i in range(1,4): # 1,2,3 用户最多可以玩3次
            my_num = int(input('请玩家输入所猜的数字:'))
            if my_num == number :
                print(f'恭喜你，猜中了，就是数字{my_num}')
                break
            elif my_num > number :
                print(f'你猜的数字太大了，还剩下{3-i}次')
            else:
                print(f'你猜的数字太小了，还剩下{3-i}次')
        else: #三次都猜错
            print(f'三次都错了，正确的答案是{number}')
    elif order == 'no' or order == 'n': #不想玩了
        print('game over')
        break
    else :
        print('请输入正确的指令')