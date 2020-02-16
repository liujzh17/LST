from scipy.interpolate import Rbf
import numpy as np
from osgeo import gdal
import lwr
from pyhdf.SD import SD,SDC
import os




def tps(data_T,data_31,QA=False):
    '''
    QA为Ture时，不会过滤结果，会生成精度评价文件
    QA为False时，会过滤结果，过滤阈值为Q3+1.5*（Q3-Q1），不会生成精度评价文件
    '''
    #调入定位信息
    name = "data\\Tibet\\2020-01-05.hdf"
    file = SD(name)
    location = file.attributes()
    uplift_tem1 = location.get('StructMetadata.0').split('\n')[7]
    uplift_tem2 = uplift_tem1.split("(")[1].strip(")")
    uplift = uplift_tem2.split(',')
    lowright_tem1 = location.get('StructMetadata.0').split('\n')[8]
    lowright_tem2 = lowright_tem1.split("(")[1].strip(")")
    lowright = lowright_tem2.split(',')

    #调入高程信息
    DEM_name = 'data\\GMTED2010'
    DEM_file = gdal.Open(DEM_name)
    GT = DEM_file.GetGeoTransform()

    '''
            Xgeo = GT(0) + Xpixel * GT(1) + Yline * GT(2)
            Ygeo = GT(3) + Xpixel * GT(4) + Yline * GT(5)
            像元行列数与经纬度的关系式
    '''

    #计算目标位置
    Xgeo, Ygeo = uplift
    Xgeo = float(Xgeo)
    Ygeo = float(Ygeo)
    Xline = (Xgeo * GT[5] - GT[0] * GT[5] - Ygeo * GT[2] + GT[3] * GT[2]) / (GT[1] * GT[5] - GT[2] * GT[4])
    Yline = (Ygeo * GT[1] - GT[3] * GT[1] - Xgeo * GT[4] + GT[0] * GT[4]) / (GT[1] * GT[5] - GT[2] * GT[4])
    X_min = int(Xline)
    Y_min = int(Yline)
    data_elevation = DEM_file.ReadAsArray(X_min, Y_min, 1200, 1200)

    #调入温度数据和波段31数据
    data_temperature = data_T
    data_band31 = data_31

    QA_data=[]
    for i in data_temperature:
        if i != -70:
            QA_data.append(i)

    # 过滤值域计算
    zheng = []
    fan = []
    QA_data.sort()
    for i in QA_data:
        zheng.append(i)
    QA_data.sort(reverse=True)
    for i in QA_data:
        fan.append(i)
    Q1 = int(len(QA_data) // 4)
    Q2 = int(len(QA_data) // 4 * 3)
    Qmax = zheng[Q2 - 1] + 1.5 * (zheng[Q2 - 1] - zheng[Q1 - 1])
    Qmin = fan[Q2 - 1] + 1.5 * (fan[Q2 - 1] - fan[Q1 - 1])


    #进行TPS模型建立
    data_TPS = []
    for i in range(len(data_temperature)):
        data_TPS1 = []
        row = i // 1200
        column = i % 1200
        data_TPS1.append(data_elevation[row][column])
        data_TPS1.append(data_band31[i])
        data_TPS1.append(data_temperature[i])
        data_TPS1.append(int(GT[0] + row * GT[1] + column * GT[2]))
        data_TPS1.append(int(GT[3] + row * GT[4] + column * GT[5]))
        data_TPS.append(data_TPS1)
    useful_data=[]
    for i in range(len(data_TPS)):
        if data_TPS[i][1] != 0:
            if data_TPS[i][2] != -70:
                useful_data.append(data_TPS[i])
    count=1
    x = []
    y = []
    z = []
    Xarr = []
    Yarr = []
    for i in range(500):
        tool_num=int(len(useful_data)*count/500)-1
        x.append(useful_data[tool_num][0])
        y.append(useful_data[tool_num][1])
        z.append(useful_data[tool_num][2])
        Xarr.append(useful_data[tool_num][3])
        Yarr.append(useful_data[tool_num][4])
        count+=1

    rbfi=Rbf(x,y,Xarr,Yarr,z,function="thin_plate")
    time=0
    if QA==True:
        accuracy=[]
        A_TPS=0
        fin_data=[]
        for i in range(len(data_TPS)):
            if data_TPS[i][1] != 0:
                hat = rbfi(data_TPS[i][0], data_TPS[i][1],data_TPS[i][3],data_TPS[i][4])
                hat = round(float(hat),2)
                if data_TPS[i][2] == -70.00:
                    pass
                else:
                    A_TPS=abs(hat-data_TPS[i][2])
                    accuracy.append(A_TPS)
                    hat=data_TPS[i][2]
            else:
                hat = data_TPS[i][2]
            if hat > Qmax or hat < Qmin and hat != -70.00:
                time+=1
            fin_data.append(hat)
        #精度评价
        mean=sum(accuracy)/len(accuracy)
        f=open('空间插值精度.txt','w')
        f.write('TPS模拟点个数为：{}\nTPS异常值点数目为：{}\n最大值：{}\n最小值:{}\n平均值:{}'.format(len(x),time,max(accuracy),min(accuracy),mean))
        f.close()



    else:
        fin_data = []
        for i in range(len(data_TPS)):
            if data_TPS[i][1] != 0:
                hat = rbfi(data_TPS[i][0], data_TPS[i][1],data_TPS[i][3],data_TPS[i][4])
                hat = round(float(hat),2)
                if data_TPS[i][2] == -70.00:
                    pass
                else:
                    hat = data_TPS[i][2]
            else:
                hat = data_TPS[i][2]
            if hat > Qmax or hat < Qmin and hat != -70.00:
                hat = -70.00
            fin_data.append(hat)

    return fin_data



def band31_lwr():
    print('开始band31处理')
    # 准备一个临时数据用以储存回归所需数据
    tem_data = []

    # 调入所有的数据
    path = r'data\\Tibet'
    for filename in os.listdir(path):
        HDF_FILR_URL = path + '\\\\' + filename

        # 整理band31数据
        file = SD(HDF_FILR_URL)
        band31 = file.select('Emis_31').get()
        band31_data = []
        for i in range(1200):
            for k in range(1200):
                band31_data.append(band31[i][k])
        tem_data.append(band31_data)
    print('开始插值')
    # 时间序列补充
    count=0
    new_data = []
    for i in range(len(tem_data[3])):
        if tem_data[3][i] != 0:
            Hat = tem_data[3][i]
            new_data.append(Hat)
        else:
            dataSet = []
            Labels = []
            Hat = 0
            for k in range(7):
                if tem_data[k][i]==0:
                    pass
                else:
                    dataSet.append([1, k + 1])
                    Labels.append(tem_data[k][i])
            if dataSet==[] or len(dataSet)==1:
                Hat=0
            else:
                Hat = lwr.lwlr([1, 4], dataSet, Labels)
                if Hat==None:
                    Hat=0
                else:
                    Hat = round(float(Hat), 2)
            if Hat == 0:
                count +=1  # 处理空值
            new_data.append(Hat)

    print('波段31缺失值：{}'.format(count))

    f = open('band31.txt', 'w')
    f.write(str(new_data))
    f.close()

    return new_data

