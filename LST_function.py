# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on : 2020/2/19 13:05

@Author : jz liu
"""

import numpy as np
import pandas as pd
import datetime

from sklearn.linear_model import LinearRegression
from scipy.interpolate import Rbf
from pyhdf.SD import SD,SDC
from osgeo import gdal
from os import listdir, path
from osgeo import osr


class download:
#  some functions for downloading and collecting
    def __init__(self):
        pass

class process:
#  some functions like Projection transformation,etc
    def __init__(self,dir_data,filv=-125):
        #第一个参数是数据地址，第二个参数是你想用作填充空值的值
        self.dir=dir_data
        self.filv=filv

    def getFile_Test(self):
        #获取数据文件列表,供测试版使用（只有7天数据）
        flist = np.sort(listdir(self.dir))

        return flist

    def getFile(self,year,month,date):
        #获取距插值日期最近的7天数据名称
        list_sort = []
        filename = '{}-{}-{}'.format(year,month,date)
        d = datetime.datetime.strptime(filename, '%Y-%m-%d')
        for i in range(-3,4):
            delta = datetime.timedelta(days=i)
            list_sort.append('{}.hdf'.format(str(d + delta)[:10]))

        return list_sort

    def int2bin(self,data):
        #将整数转化为二进制，只使用于QC指数的获取
        data_bin = [bin(vi)[2:][-2::] for vi in data.reshape(data.size)]
        data_bin = np.array(data_bin).reshape(data.shape)
        return data_bin

    def getData(self,file,var,DayNightFlag=None):
        '''
        获取数据内容
        :param file: 文件名
        :param var: 需要的数据集
        :param DayNightFlag: 白天或是晚上
        :return: 经过0值处理过的数据集
        '''
        if var == 'LST':
            varName = 'LST_{}_1km'.format(DayNightFlag)
            data = SD('{}\\{}'.format(self.dir,file)).select(varName).get()
            data = data  * 0.02 - 273.15
            data[data == -273.15] = self.filv
        elif var == 'QC':
            varName = 'QC_{}'.format(DayNightFlag)
            data = SD('{}\\{}'.format(self.dir,file)).select(varName).get()
            data = self.int2bin(data)
        elif var == 'BAND31':
            varName = 'Emis_31'
            data = SD('{}\\{}'.format(self.dir,file)).select(varName).get()
            data = data.astype('int')
            data[data == 0] = self.filv

        return data

    def QualityControl(self,LST_data,QC_data,level=4):
        '''
        得到符合质量要求的LST数据
        :param LST_data: LST数据
        :param QC_data: QC数据
        :param level: 希望过滤的质量等级
                        1：全部过滤
                        2：只保留1级数据
                        3：保留1，2级数据
                        4：保留1，2，3级数据
        :return: 经过质量指数过滤后的LST数据
        '''
        if level > 2:
            if level == 3:
                value = '10'
            elif level == 4:
                value = '11'
        else:
            if level == 2:
                value = '01'
            elif level == 1:
                value = '00'
        mask = QC_data >= value
        LST_data[mask] = self.filv

        return LST_data

    def InforFind(self,data):
        #用于查找坐标数据，只为getCoordinate函数服务
        return 'UpperLeftPointMtrs' in data

    def getCoordinate(self,file):
        '''
        获得数据左上角坐标
        :param file: 文件名
        :return: 左上角的经度和纬度（投影坐标系，单位：米）
        '''
        location = SD('{}\\{}'.format(self.dir,file)).attributes()
        uplift_tem1 = location.get('StructMetadata.0').split('\n')
        uplift_tem2 = list(filter(self.InforFind,uplift_tem1))[0]
        start = uplift_tem2.find('(')
        middle = uplift_tem2.find(',')
        end = uplift_tem2.find(')')
        x=uplift_tem2[start+1:middle]
        y=uplift_tem2[middle+1:end]

        return float(x),float(y)

    def XY2Line(self,x,y,flag=True,Xuplift=None,Yuplift=None):
        '''
        正弦投影坐标在图上对应的行列数，flag=Ture,返回在高程图上的行列数，flag=Flase，返回在指定图上的行列数
        :param x: 左上角经度（投影坐标系，单位：米）
        :param y: 左上角纬度（投影坐标系，单位：米）
        :param flag:是否返回在高程图上的行列数
        :param Xuplift:指定图左上角x坐标
        :param Yuplift:指定图左上角y坐标
        :return: 左上角所在的列、行数
        '''
        DEM_name = 'data\\GMTED2010'
        DEM_file = gdal.Open(DEM_name)
        GT = DEM_file.GetGeoTransform()
        if flag == False:
            X = Xuplift
            Y = Yuplift
        elif flag == True:
            X = GT[0]
            Y = GT[3]
        Xgeo = x
        Ygeo = y
        Xline = (Xgeo * GT[5] - X * GT[5] - Ygeo * GT[2] + Y * GT[2]) / (GT[1] * GT[5] - GT[2] * GT[4])
        Yline = (Ygeo * GT[1] - Y * GT[1] - Xgeo * GT[4] + X * GT[4]) / (GT[1] * GT[5] - GT[2] * GT[4])
        X_min = int(Xline)
        Y_min = int(Yline)

        return X_min,Y_min

    def getDemData(self,x,y):
        '''
        获取高程数据
        :param x: 左上角经度（投影坐标系，单位：米）
        :param y: 左上角纬度（投影坐标系，单位：米）
        :return: 目标数据的对应高程数据
        '''
        X_min,Y_min = self.XY2Line(x,y)
        DEM_name = 'data\\GMTED2010'
        DEM_file = gdal.Open(DEM_name)
        GT = DEM_file.GetGeoTransform()

        data_elevation = DEM_file.ReadAsArray(X_min, Y_min, 1200, 1200)
        data_elevation = np.array(data_elevation).reshape(1200,1200)
        data_elevation = data_elevation.tolist()

        return data_elevation

    def getLonLat(self,x,y):
        '''
        获取全局的经纬度（投影坐标系，单位：米）
        :param x: 左上角经度（投影坐标系，单位：米）
        :param y: 左上角纬度（投影坐标系，单位：米）
        :return: 目标数据对应的经纬度数据（投影坐标系，单位：米）
        '''
        File_name = 'data\\GMTED2010'
        File = gdal.Open(File_name)
        GT = File.GetGeoTransform()
        Lon_data = [int(x + k * GT[1] + i * GT[2]) for i in range(1200) for k in range(1200)]
        Lat_data = [int(y + k * GT[4] + i * GT[5]) for i in range(1200) for k in range(1200)]
        Lon_data = np.array(Lon_data).reshape(1200,1200)
        Lat_data = np.array(Lat_data).reshape(1200,1200)
        Lon_data = Lon_data.tolist()
        Lat_data = Lat_data.tolist()
        return Lon_data,Lat_data

    def getSRSPair(self):
        #获取modis数据对应的地理坐标系，投影坐标系信息
        # （为方便阅读，特此说明）
        # （由于modis数据无自带的hdr文件，无法直接得到投影信息，
        #   故参照modis数据的坐标系参数，已将GMTED数据转换为相应坐标系，其坐标系现与modis相同）
        dataset = gdal.Open('data\\GMTED2010')
        prosrs = osr.SpatialReference()
        prosrs.ImportFromWkt(dataset.GetProjection())
        geosrs = prosrs.CloneGeogCS()
        return prosrs, geosrs

    def geo2lonlat(self,x,y):
        '''
        将投影坐标转换为自身对应的地理坐标，在主函数中未使用，只写下备用
        :param x: 经度（投影坐标系，单位：米）
        :param y: 纬度（投影坐标系，单位：米）
        :return: 经纬度（地理坐标系，单位：度）
        '''
        prosrs, geosrs = self.getSRSPair()
        ct = osr.CoordinateTransformation(prosrs, geosrs)
        coords = ct.TransformPoint(x, y)

        return coords[:2]

    def GeoTransfor(self,x,y,out_epsg=4326):
        '''
        将目标经纬度转化为需要的坐标系
        常用的EPSG：
                    WGS_84 = 4326
        :param x: 经度（投影坐标系，单位：米）
        :param y: 纬度（投影坐标系，单位：米）
        :param out_epsg: 转化后的坐标系对应的EPSG
        :return: 转换后的经纬度
        '''
        prosrs, geosrs = self.getSRSPair()
        prosrs_WGS = osr.SpatialReference()
        prosrs_WGS.ImportFromEPSG(out_epsg)
        ct = osr.CoordinateTransformation(prosrs, prosrs_WGS)
        for i in range(1200):
            for k in range(1200):
                lon,lat = ct.TransformPoint(x[i][k],y[i][k])[:2]
                x[i][k],y[i][k] = lon,lat

        return x,y

    def WGS2NUM(self,x,y,xuplife,yuplife):
        '''
        将WGS84坐标下的坐标转化为目标图像的行列数
        :param x: 纬度（地理坐标，单位：度）
        :param y: 经度（地理坐标，单位：度）
        :param xuplife: 经度（投影坐标，单位：米）
        :param yuplife: 纬度（投影坐标，单位：米）
        :return: 行、列数
        '''
        prosrs, geosrs = self.getSRSPair()
        prosrs_WGS = osr.SpatialReference()
        prosrs_WGS.ImportFromEPSG(4326)
        ct = osr.CoordinateTransformation( prosrs_WGS, prosrs)
        X_sin , Y_sin = ct.TransformPoint(x,y)[:2]
        X,Y = self.XY2Line(X_sin,Y_sin,False,xuplife,yuplife)

        return Y,X

    def getSiteData(self):
        #在质量评价版本中使用，获得检测站点的经纬度
        #格式为[[site,lon,lat]]
        site_data = pd.read_csv('data\\GSTObs.csv', usecols=['site', 'lat', 'lon'])
        site_data = site_data.drop_duplicates(subset='site')
        site = []
        for i in range(len(site_data)):
            site.append([site_data.iloc[i][0],int(site_data.iloc[i][1])/100,int(site_data.iloc[i][2])/100])

        return site

class interpolation:
#  some functions for temporal or spacial interpolation
    def __init__(self,filv=-125):
        self.filv = filv

    def Effective(self,Yvalue):
        #获得非空值所在的位置
        num = []
        for value in range(len(Yvalue)):
            if Yvalue[value] != self.filv:
                num.append(value)
        return num

    def lwrFilter(self,XYflag,Yvalue,num=None,weights=None):
        '''
        计算空值和权重，在lwr函数内部使用
        :param XYflag:
                        X：获取所需权重数据
                        Y：获取可用的y数据
        :param Yvalue: y数据
        :param num: 非空值坐在位置，只在XYflag = Y 时输入
        :param weights: 整体权重数据，只在XYflag = X 时输入
        :return:
                XYflag = Y ：可用y数据
                XYflag = X ：所需权重数据
        '''
        if XYflag == 'Y':
            while self.filv in Yvalue:
                Yvalue.remove(self.filv)

            return np.mat(Yvalue)

        elif XYflag == 'X':

            weight = np.mat(np.eye((len(num))))
            for j in range(len(num)):
                weight[j,j] = weights[num[j]]

            return np.mat(weight)

    def countXTX(self,Flag,num=None,X=None,Xmat=None,weight=None):
        '''
        计算Xmat时，Flag=True，添加num，X参数
        计算xTx时，Flag=False，添加Xmat，weight参数
        '''
        if Flag == True:
            xmat = []
            for j in range(len(num)):
                xmat.append(X[num[j]])
            return np.mat(xmat)

        elif Flag == False:
            xTx = Xmat.T * (weight * Xmat)

            return np.mat(xTx)

    def countLWR(self,y,testPoint,weights,xArr):
        #具体计算lwr结果，在lwr函数内部使用

        y = y.tolist()
        if y[testPoint[1] - 1] != self.filv:  # 判断是否需要插值
            ws1 = y[testPoint[1] - 1]
        else:
            num = self.Effective(y)
            if len(num) < 2 or len(num) == 2 and abs(y[num[0]]-y[num[1]]) > 10:  # 判断是否可以插值
                ws1 = y[testPoint[1] - 1]
            else:# 如果符合两个条件

                weight = self.lwrFilter('X', y, num=num, weights=weights)
                xmat = self.countXTX(True, num=num, X=xArr)
                xTx1 = self.countXTX(False, Xmat=xmat, weight=weight)
                if np.linalg.det(xTx1) == 0.0:
                    print("This matrix is singular, cannot do inverse")
                    ws1 = y[testPoint[1] - 1]
                else:

                    ws1 = xTx1.I * (xmat.T * (weight * self.lwrFilter('Y', y).T))
                    ws1 = int(testPoint * ws1)

        return ws1

    def lwr(self,testPoint,xArr,yArr,k=1.0):
        '''
        lwr核心计算函数，为了可视化方便，均以【1，】形式输入
        :param testPoint: 需要插值的点
        :param xArr: x轴数据
        :param yArr: y轴数据（1200*1200*N格式）
        :param k: 权重调整指数，k=1时权重按照标准正态分布计算
        :return: 插值后的数据，数据位置经过转置，输出后需要重新转置得到正确结果
        '''
        xMat = np.mat(xArr); yMat = np.array(yArr).T
        m = np.shape(xMat)[0]

        weights = []
        for j in range(m):                      #next 2 lines create weights matrix
            diffMat = testPoint - xMat[j,:]   #difference matrix
            weights.append(np.exp(diffMat*diffMat.T/(-2.0*k**2)))#weighted matrix

        ws = [self.countLWR(y,testPoint,weights,xArr) for array in yMat for y in array]

        return ws

    def getTrainingPoint(self,data):
        #data为转置后的五项数据，只在TPS函数内部使用

        avail_point=[]

        for value in data:
            for y in value:
                if y[0] != self.filv:
                    if y[1] != self.filv:
                        avail_point.append(y)

        TrPoint = []

        for i in range(500):
            num = int(len(avail_point)/500)*i
            TrPoint.append(avail_point[num])
        TrPoint = np.array(TrPoint).T
        TrPoint = TrPoint.tolist()
        del avail_point

        return TrPoint

    def linear(self,trainpoint):
        '''
        计算协因数系数
        :param trainpoint:
                            训练点
        :return:
                a：高程系数
                b：发射率系数
        '''
        reg = LinearRegression()

        c = np.array(trainpoint[1]).flatten()
        d = np.array(trainpoint[2]).flatten()

        X = np.column_stack((c,d))
        Y = np.array(trainpoint[0]).reshape(-1,1)

        reg.fit(X,Y)

        tem = reg.coef_.flatten()
        a = tem[0]
        b = tem[1]

        return a,b

    def TPS(self,LST_Data,BAND31_Data,ELE_Data,Lon_Data,Lat_Data,Filter):
        '''
        进行TPS插值
        :param LST_Data: LST数据
        :param BAND31_Data: 波段31数据
        :param ELE_Data: 高程数据
        :param Lon_Data: 经度数据（投影坐标系，单位：米）
        :param Lat_Data: 纬度数据（投影坐标系，单位：米）
        :param Filter:
                        True：按照阈值过滤结果
                        Flase:不过滤结果
        :return: TPS后的LST数据
        '''

        data=[]
        data.append(LST_Data)
        data.append(ELE_Data)
        data.append(BAND31_Data)
        data.append(Lon_Data)
        data.append(Lat_Data)
        data = np.array(data).T
        data = data.tolist()

        trainPoint = self.getTrainingPoint(data)
        a,b = self.linear(trainPoint)
        print(a,b)

        ELE = np.array(trainPoint[1])
        BAND31 = np.array(trainPoint[2])
        LST = np.array(trainPoint[0])
        LST_tem = LST - a*ELE - b*BAND31

        rbfi = Rbf(trainPoint[3], trainPoint[4],LST_tem, function="thin_plate")


        if Filter == True:
            max, min = self.QAcount(LST_Data)
            data = []

            for i in range(1200):

                for k in range(1200):

                    if LST_Data[i][k] != self.filv:  # 是否需要插值

                        data.append(LST_Data[i][k])

                    elif BAND31_Data[i][k] == self.filv:  # 是否可以插值

                        data.append(self.filv)

                    else:  # 满足两个条件

                        value = rbfi(Lon_Data[i][k], Lat_Data[i][k])
                        value = value + a*ELE_Data[i][k] + b*BAND31_Data[i][k]

                        if value > max or value < min:
                            value = self.filv

                        data.append(value)


        elif Filter == False:
            data = []

            for i in range(1200):

                for k in range(1200):

                    if LST_Data[i][k] != self.filv:  # 是否需要插值

                        data.append(LST_Data[i][k])

                    elif BAND31_Data[i][k] == self.filv:  # 是否可以插值

                        data.append(self.filv)

                    else:  # 满足两个条件

                        value = rbfi(Lon_Data[i][k], Lat_Data[i][k])
                        value = value + a * ELE_Data[i][k] + b * BAND31_Data[i][k]

                        data.append(value)

        data = np.array(data).reshape(1200, 1200).tolist()


        return data

    def QAcount(self,LST_data):
        '''
        计算filter的阈值，只在TPS函数内部使用
        :param LST_data: LST数据
        :return: Filter的上下限
        '''
        LST_data = [y for i in LST_data for y in i if y != self.filv]

        Q1 = int(len(LST_data) // 4)
        Q2 = int(len(LST_data) // 4 * 3)
        LST_data.sort()
        Qmax = LST_data[Q2 - 1] + 1.5 * (LST_data[Q2 - 1] - LST_data[Q1 - 1])
        Qmin = LST_data[Q1 - 1] + 1.5 * (LST_data[Q1 - 1] - LST_data[Q2 - 1])

        return Qmax,Qmin

class data_show:
#  some functions for organizing and showing the data
    def __init__(self,filv):
        self.filv=filv

    def BuildFlag(self,TPS_data,LWR_data,ORI_data):
        '''
        获取结果数据的flag
        :param TPS_data: 空间插值结果
               LWR_data: 时间插值结果
               ORI_data: 源数据
        :return: 数据来源矩阵
                0：无值
                1：原数据所得
                2：时间插值所得
                3：空间插值所得

        '''
        Flag = [[0]*1200]*1200
        Flag = np.array(Flag)

        TPS_data = np.array(TPS_data)
        LWR_data = np.array(LWR_data)
        ORI_data = np.array(ORI_data)

        Flag[TPS_data != self.filv ] = 3
        Flag[LWR_data != self.filv ] = 2
        Flag[ORI_data != self.filv ] = 1

        return Flag




