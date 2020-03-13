# !/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on : 2020/3/9 12:25

@Author : jz liu
'''
'''
精度评价版本（第2版）完成于 2020/3/11 可以生成一个针对于观测站点的csv数据集 
相较于第一版
改进：
    1.去除了不必要的计算过程，速度有了一定提升，一景数据约耗时5min
    2.增加了提取多点和转换投影功能，简单的对每日四个时刻进行了平均
    3.对源数据地址选取进行了改进，可以根据需要的日期自动匹配需要的数据名称

尚存在的不足：
    1.投影转换只是单纯计算个个点对应的坐标，没有生成新的地理数据集
    2.算法依然采用了大量的整体遍历，效率没有复杂度层面上的提高
    3.核心函数的多态性较差，只能完成规定数据格式的操作
'''
from LST_function import download,process,interpolation,data_show
import numpy as np
import gc
import pandas as pd
import copy

# ============ 设置 ================================================
dir1_data = r'data\\Tibet\\aqua'
dir2_data = r'data\\Tibet\\terra'
filv = -125
INTLWR1 = [[1,1],[1,2],[1,3],[1,4],[1,5]]
INTLWR2 = [[1,1],[1,2],[1,3],[1,4],[1,5],[1,6],[1,7]]
WGS_EPSG = 4326

# =========== 获取公共数据（经纬度，高程）================================

list = process(r'data\\Tibet')
x,y = list.getCoordinate('ele.hdf') #调出高程数据
Ele_Data = list.getDemData(x,y)

Lon_data,Lat_data = list.getLonLat(x,y) #经纬度数据

# =========== 提取站点所在的行列数 ========================================
site = list.getSiteData()
site_num = []
for i in site:
    column,row = list.WGS2NUM(i[1],i[2],x,y)
    if   0 < column < 1200 and 0 < row < 1200: #如果站点在这一景数据中
        site_num.append([column,row,i[0],i[1],i[2]])
print('此景内共有观测站{}个'.format(len(site_num)))
del site
gc.collect() #释放内存

# =========== 创建一个csv数据 ================================================
df = pd.DataFrame(columns=['column','row','site','lat','lon','year','month','date','aqua_day','flag','aqua_night','flag','terra_day','flag','terra_night','flag','lstAvg'])
df.to_csv('OctoberLST.csv',index=False)
# ======= 文件的名称获取 ===============================================================
for date in range(1,32):        #获取10月份所有的数据
    list_sort = list.getFile(2019,10,date)

    tem_csv = copy.deepcopy(site_num)  #每处理完一天的数据清0重新输入


    gc.collect() # 释放上一日数据中的缓存

    for i in tem_csv:    #写入年月日数据
        i.append(2019)
        i.append(10)
        i.append(date)
# ===================================================================================
    #两个卫星的数据
    for dir_data in [dir1_data,dir2_data]:

        list_tem = process(dir_data, filv=filv)

        #早晚的数据
        for daynight in ['Day','Night']:
# =============== 获取数据 =============================================================
            tem_LstData = []  # 调出lst数据
            for i in list_sort[1:6]:
                LST_data = list_tem.getData(i, 'LST', DayNightFlag=daynight)
                QC_data = list_tem.getData(i, 'QC', DayNightFlag=daynight)
                data = list_tem.QualityControl(LST_data, QC_data)
                tem_LstData.append(data)

            tem_Band31Data = []  # 调出band31数据
            for i in list_sort:
                BAND31_data = list_tem.getData(i, 'BAND31')
                tem_Band31Data.append(BAND31_data)
# =============== 插值 ==============================================================
            INT = interpolation(filv)
            LST_lwrData = INT.lwr([1, 3], INTLWR1, tem_LstData)  # LST数据时间插值
            LST_lwrData = np.array(LST_lwrData).reshape(1200, 1200).T.tolist()
            del tem_LstData

            BAND31_lwrData = INT.lwr([1, 4], INTLWR2, tem_Band31Data)  # band31数据时间插值
            BAND31_lwrData = np.array(BAND31_lwrData).reshape(1200, 1200).T.tolist()
            del tem_Band31Data

            gc.collect()  #释放时间插值过程中的无用内存

            LST_tpsData = INT.TPS(LST_lwrData,BAND31_lwrData,Ele_Data,Lon_data,Lat_data,True)#空间序列插值1
            LST_tpsData = INT.TPS(LST_tpsData,BAND31_lwrData,Ele_Data,Lon_data,Lat_data,False)#空间序列插值2
            del BAND31_lwrData

            gc.collect()  #释放空间插值过程中的无用内存

            SHOW = data_show(filv)
            LST_data = list_tem.getData('2019-10-{:0>2}.hdf'.format(date),'LST',DayNightFlag=daynight)
            Flag = SHOW.BuildFlag(LST_tpsData,LST_lwrData,LST_data)  #创建数据来源矩阵



            for everysite in tem_csv:     #写入LST和flag
                everysite.append(LST_tpsData[everysite[0]][everysite[1]])
                everysite.append(Flag[everysite[0]][everysite[1]])

    for everysite in tem_csv:   #写入平均值
        if everysite[9] != 0 and everysite[11] != 0 and everysite[13] != 0 and everysite[15] != 0: #如果四个数据全部有值
            everysite.append((everysite[8]+everysite[10]+everysite[12]+everysite[14])/4)
        else: #至少有一个数值为无值
            everysite.append('Wrong')

    everyday = pd.DataFrame(tem_csv)
    everyday.to_csv('OctoberLST.csv',mode='a',header=False,index=False)

    print('2019-10-{}数据处理完成'.format(date))

    del everyday


