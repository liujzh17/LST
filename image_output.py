import matplotlib.pyplot as plt
import matplotlib
import numpy as np

def correct(data):
    # 为了输出正确坐标关系的图形倒序列表
    start = 0
    end = 1
    long = len(data)/1200
    data2 = []
    while end <= 1200:
        data1=data[int(long*start):int(long*end)]
        data2.append(data1)
        start += 1
        end += 1
    data2.reverse()
    data3=[]
    for i in data2:
        for k in i:
            data3.append(k)

    return data3

class ImageMake:
    def __init__(self,row,column,data):
        self.data = np.array(data).reshape(row,column)
    def OutPut(self,data,color='bwr'):

        #出图
        plt.imshow(data, interpolation='nearest', cmap=color, origin='lower')
        plt.colorbar()

        plt.xticks(())
        plt.yticks(())
        plt.show()