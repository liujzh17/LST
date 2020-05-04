# !/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on : 2020/5/3 17:27

@Author : jz liu
'''

# =================== 如果想只生成结果文件，不生成精度评价文件 ============================
'''
from LST_Run import Run

date     = ['2019-01-01','2019-01-03']
block    = ['h24v05']
dir_data = r'data'
filv     = 0
espg     = 4326

tryOne = Run(date,block,dir_data,filv,espg)
tryOne.main()
'''
# ======================= 一些说明 ===================================================
#
#   1) espg编码： WGS84 = 4326
#
#   2) 注意将LST.Run,LST_download,LST_function，data文件夹，rusult文件夹和你的程序放在同一个目录下
#       高程数据放在data文件夹下，下载程序和运行程序的数据地址保持一致
#
#   3）python库信息与requirements.txt内要求尽量保持一致，特别是gdal库
#
#   4) 进度条最后4%时不要停止程序，会导致结果数据不完整，但是再次计算时会按照计算完成而跳过！！！
#
#   5）为了减少计算量，进度条只会在一次整体遍历后改变，进度条长时间不动（1~3分钟）为正常情况
#
#   6）各个部分依靠数据的名称连接，不要改变数据的名称
#
# ================ 如果想生成一个记录站点位置平均地温的csv文件并生成结果文件 ==============
'''
from LST_Run import Run_AC

date      = ['2019-01-01','2019-01-03']
block     = ['h24v05']
dir_data  = r'data'
filv      = 0
site_data = [[52602,38.45,93.20],[52787,37.12,102.52]]
csv_name  = 'Tibet_2019-01-01~2019-01-03'
espg      = 4326

tryOne = Run_AC(date,block,dir_data,filv,site_data,csv_name,espg)
tryOne.main()
'''

# ========== 一些说明 ============================================================
#
#   1）在run方法的注意事项外，还应注意在最后4%时不要关闭程序，不然会造成csv和tif文件生成不匹配的情况
#      同时，如果想在原有csv上继续录入数据，要注意有无重复数据，程序没有检验csv中是否存在该数据的功能
#
#   2) LST_function.process中有一个针对csv提取site_data的方法，如果不想手动输入站点信息可以参考
#       那个方法
#
# ================== 拼接影像 ==========================================================
'''
from LST_Run import Splicing

date     = ['2019-01-01','2019-01-01']
block    = ['h23v05','h24v05']
dir_data = r'result\SIN'
dir_out  = r'result'
filename = 'Tibet'
Nodata   = 0

tryOne = Splicing(date,block,dir_data,dir_out,filename,Nodata)
tryOne.main()
'''
# ============== 一些说明 ========================================================
#
#   1）输入数据必须是正弦投影数据，程序会在拼接正弦投影数据之后再生成WGS84投影数据，数据的投影
#      会在数据名中体现
#
#   2) 因为这个方法命名比较自由，所以没有查重功能
#
#   3）如果块不相邻，没有数据的地方默认为0，可以通过Nodata参数调整，建议Nodata与Run中filv保持一致
#      同时尽量选择相邻的数据拼接
#




from LST_function import process,interpolation,data_show,progress_bar
from osgeo import gdal
import pandas as pd
import numpy as np
import datetime
import copy
import gc
import re
import os

class Run:
    def __init__(self,date,block,dir_data,filv,espg=4326):
        '''

        :param date:  [开始日期({}-{}-{}),结束日期({}-{}-{})]
        :param block: 所有块编号[h??v??,h??v??,...]
        :param dir_data: 数据地址
        :param filv: 想用作填充空值的值
        :param espg: 转换投影之后的投影espg编码
        '''

        self.date     = date
        self.block    = block
        self.dir_data = dir_data
        self.filv     = filv
        self.espg     = espg

    def count_day(self,date,block,Ele_Data,Lon_data,Lat_data,GeoTransform):
        '''
        计算一日的平均地温，生成原投影平均地温文件和转换投影后的平均地温数据
        :param date: 日期
        :param block: 块编号
        :param Ele_Data: 高程数据
        :param Lon_data: 经度数据
        :param Lat_data: 纬度数据
        :param GeoTransform: 仿射信息
        '''
        INTLWR1 = [[1, 1], [1, 2], [1, 3], [1, 4], [1, 5]]
        INTLWR2 = [[1, 1], [1, 2], [1, 3], [1, 4], [1, 5], [1, 6], [1, 7]]

        processor = process(self.dir_data,self.filv)

        time      = re.search(r'(\d*)-(\d*)-(\d*)',date)

        File_list = processor.getFile(time.group(1),time.group(2),time.group(3))

        Flag = [[0] * 1200] * 1200
        Flag = np.array(Flag)
        Average = [[0] * 1200] * 1200
        Average = np.array(Average)

        progress = progress_bar(25, '{} {} '.format(block,date))
        now      = 0
        progress.show_now(now)
        for satellite in ('MOD11A1','MYD11A1'):

            for daynight in ['Day','Night']:

                tem_LstData = []  # 调出lst数据
                for i in File_list[1:6]:
                    LST_data = processor.getData('MODIS_{}_V006_{}_{}.hdf'.format(satellite,block,i), 'LST', DayNightFlag=daynight)
                    QC_data  = processor.getData('MODIS_{}_V006_{}_{}.hdf'.format(satellite,block,i), 'QC', DayNightFlag=daynight)
                    data = processor.QualityControl(LST_data, QC_data)
                    tem_LstData.append(data)

                tem_Band31Data = []  # 调出band31数据
                for i in File_list:
                    BAND31_data = processor.getData('MODIS_{}_V006_{}_{}.hdf'.format(satellite,block,i), 'BAND31')
                    tem_Band31Data.append(BAND31_data)


                INT = interpolation(self.filv)
                LST_lwrData = INT.lwr([1, 3], INTLWR1, tem_LstData)  # LST数据时间插值
                LST_lwrData = np.array(LST_lwrData).reshape(1200, 1200).T.tolist()
                now += 3
                progress.show_now(now)
                del tem_LstData

                BAND31_lwrData = INT.lwr([1, 4], INTLWR2, tem_Band31Data)  # band31数据时间插值
                BAND31_lwrData = np.array(BAND31_lwrData).reshape(1200, 1200).T.tolist()
                now += 1
                progress.show_now(now)
                del tem_Band31Data

                gc.collect()  # 释放时间插值过程中的无用内存

                LST_tpsData = INT.TPS(LST_lwrData, BAND31_lwrData, Ele_Data, Lon_data, Lat_data, True)  # 空间序列插值1
                now += 1
                progress.show_now(now)
                LST_tpsData = INT.TPS(LST_tpsData, BAND31_lwrData, Ele_Data, Lon_data, Lat_data, False)  # 空间序列插值2
                now += 1
                progress.show_now(now)
                del BAND31_lwrData

                gc.collect()  # 释放空间插值过程中的无用内存

                tem_data = np.array(LST_tpsData)
                Flag[tem_data == self.filv] = 1
                Average  = Average + tem_data

        Average = Average/4
        Average[Flag == 1] = self.filv

        SHOW =data_show(self.filv)
        SHOW.build_NewTif(Average,'result\\SIN\\{}_{}_Average_SIN.tif'.format(block,date),GeoTransform)
        SHOW.ReProjection('result\\SIN\\{}_{}_Average_SIN.tif'.format(block,date),'result\\WGS84\\{}_{}_Average_WGS84.tif'.format(block,date),self.espg)
        now += 1
        progress.show_now(now)
        print('')

    def getEveryDay(self,begin_date, end_date):
        # 获取范围内所有的日期

        date_list = []
        begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        while begin_date <= end_date:
            date_str = begin_date.strftime("%Y-%m-%d")
            date_list.append(date_str)
            begin_date += datetime.timedelta(days=1)
        return date_list

    def main(self):
        # 计算全部数据

        print('计算开始')
        date_list = self.getEveryDay(self.date[0], self.date[1])
        public_data = process(self.dir_data, self.filv)
        GT = public_data.getGT()

        for block_num in self.block:

            x, y = public_data.getCoordinate('MODIS_MOD11A1_V006_{}_{}.hdf'.format(block_num,date_list[0]))  # 调出高程数据
            Ele_Data = public_data.getDemData(x, y)
            Lon_data, Lat_data = public_data.getLonLat(x, y)  # 经纬度数据
            GeoTransform =(x,GT[1],GT[2],y,GT[4],GT[5])

            for date in date_list:
                if os.path.isfile('result\\SIN\\{}_{}_Average_SIN.tif'.format(block_num,date)):
                    print('{}   {}平均地温已经计算过'.format(block_num,date))
                else:
                    self.count_day(date,block_num,Ele_Data,Lon_data,Lat_data,GeoTransform)



class Run_AC:
    def __init__(self,date,block,dir_data,filv,site_data,csv_name,espg=4326):
        '''

        :param date:  [开始日期({}-{}-{}),结束日期({}-{}-{})]
        :param block: 所有块编号[h??v??,h??v??,...]
        :param dir_data: 数据地址
        :param filv: 想用作填充空值的值
        :param espg: 转换投影之后的投影espg编码
        :param site_data: 站点信息[[站点号，经度，纬度]，...]
        :param csv_name: 输出的csv的名称
        '''

        self.date      = date
        self.block     = block
        self.dir_data  = dir_data
        self.filv      = filv
        self.site_data = site_data
        self.csv_name  = csv_name
        self.espg      = espg

    def count_day(self,date,block,Ele_Data,Lon_data,Lat_data,GeoTransform,site,writeFlag):
        '''
        计算一日的平均地温，生成原投影平均地温文件和转换投影后的平均地温数据，把站点的数据写进csv
        :param date: 日期
        :param block: 块编号
        :param Ele_Data: 高程数据
        :param Lon_data: 经度数据
        :param Lat_data: 纬度数据
        :param GeoTransform: 仿射信息
        :param site: 初始站点信息
        :param writeFlag: 是否有需要写入的数据
        '''

        INTLWR1 = [[1, 1], [1, 2], [1, 3], [1, 4], [1, 5]]
        INTLWR2 = [[1, 1], [1, 2], [1, 3], [1, 4], [1, 5], [1, 6], [1, 7]]

        processor = process(self.dir_data,self.filv)

        time      = re.search(r'(\d*)-(\d*)-(\d*)',date)

        File_list = processor.getFile(time.group(1),time.group(2),time.group(3))

        Flag = [[0] * 1200] * 1200
        Flag = np.array(Flag)
        Average = [[0] * 1200] * 1200
        Average = np.array(Average)

        progress = progress_bar(25, '{} {} '.format(block,date))
        now      = 0
        progress.show_now(now)
        for satellite in ('MOD11A1','MYD11A1'):

            for daynight in ['Day','Night']:

                tem_LstData = []  # 调出lst数据
                for i in File_list[1:6]:
                    LST_data = processor.getData('MODIS_{}_V006_{}_{}.hdf'.format(satellite,block,i), 'LST', DayNightFlag=daynight)
                    QC_data  = processor.getData('MODIS_{}_V006_{}_{}.hdf'.format(satellite,block,i), 'QC', DayNightFlag=daynight)
                    data = processor.QualityControl(LST_data, QC_data)
                    tem_LstData.append(data)

                tem_Band31Data = []  # 调出band31数据
                for i in File_list:
                    BAND31_data = processor.getData('MODIS_{}_V006_{}_{}.hdf'.format(satellite,block,i), 'BAND31')
                    tem_Band31Data.append(BAND31_data)


                INT = interpolation(self.filv)
                LST_lwrData = INT.lwr([1, 3], INTLWR1, tem_LstData)  # LST数据时间插值
                LST_lwrData = np.array(LST_lwrData).reshape(1200, 1200).T.tolist()
                now += 3
                progress.show_now(now)
                del tem_LstData

                BAND31_lwrData = INT.lwr([1, 4], INTLWR2, tem_Band31Data)  # band31数据时间插值
                BAND31_lwrData = np.array(BAND31_lwrData).reshape(1200, 1200).T.tolist()
                now += 1
                progress.show_now(now)
                del tem_Band31Data

                gc.collect()  # 释放时间插值过程中的无用内存

                LST_tpsData = INT.TPS(LST_lwrData, BAND31_lwrData, Ele_Data, Lon_data, Lat_data, True)  # 空间序列插值1
                now += 1
                progress.show_now(now)
                LST_tpsData = INT.TPS(LST_tpsData, BAND31_lwrData, Ele_Data, Lon_data, Lat_data, False)  # 空间序列插值2
                now += 1
                progress.show_now(now)
                del BAND31_lwrData

                gc.collect()  # 释放空间插值过程中的无用内存

                tem_data = np.array(LST_tpsData)
                Flag[tem_data == self.filv] = 1
                Average  = Average + tem_data

                if writeFlag == True:
                    SHOWFlag = data_show(self.filv)
                    LST_data = processor.getData('MODIS_{}_V006_{}_{}.hdf'.format(satellite,block,date), 'LST', DayNightFlag=daynight)
                    Flagdata = SHOWFlag.BuildFlag(LST_tpsData, LST_lwrData, LST_data)  # 创建数据来源矩阵

                    for everysite in site:  # 写入LST和flag
                        everysite.append(LST_tpsData[everysite[0]][everysite[1]])
                        everysite.append(Flagdata[everysite[0]][everysite[1]])
                else:
                    pass
        if writeFlag == True:
            for everysite in site:  # 写入平均值
                if everysite[9] != 0 and everysite[11] != 0 and everysite[13] != 0 and everysite[15] != 0:  # 如果四个数据全部有值
                    everysite.append((everysite[8] + everysite[10] + everysite[12] + everysite[14]) / 4)
                else:  # 至少有一个数值为无值
                    everysite.append('Wrong')

            everyday = pd.DataFrame(site)
            everyday.to_csv('{}.csv'.format(self.csv_name), mode='a', header=False, index=False)
        else:
            pass

        Average = Average/4
        Average[Flag == 1] = self.filv

        SHOW =data_show(self.filv)
        SHOW.build_NewTif(Average,'result\\SIN\\{}_{}_Average_SIN.tif'.format(block,date),GeoTransform)
        SHOW.ReProjection('result\\SIN\\{}_{}_Average_SIN.tif'.format(block,date),'result\\WGS84\\{}_{}_Average_WGS84.tif'.format(block,date),self.espg)
        now += 1
        progress.show_now(now)
        print('')

    def getEveryDay(self,begin_date, end_date):
        # 获取范围内所有的日期

        date_list = []
        begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        while begin_date <= end_date:
            date_str = begin_date.strftime("%Y-%m-%d")
            date_list.append(date_str)
            begin_date += datetime.timedelta(days=1)
        return date_list

    def build_csv(self):
        #创建验证数据文件
        df = pd.DataFrame(
            columns=['column', 'row', 'site', 'lat', 'lon', 'year', 'month', 'date', 'aqua_day', 'flag', 'aqua_night',
                     'flag', 'terra_day', 'flag', 'terra_night', 'flag', 'lstAvg'])
        df.to_csv('{}.csv'.format(self.csv_name), index=False)

    def main(self):
        # 计算全部数据

        print('计算开始')
        self.build_csv()
        date_list = self.getEveryDay(self.date[0], self.date[1])
        public_data = process(self.dir_data, self.filv)
        GT = public_data.getGT()

        site =self.site_data

        for block_num in self.block:

            x, y = public_data.getCoordinate('MODIS_MOD11A1_V006_{}_{}.hdf'.format(block_num,date_list[0]))  # 调出高程数据
            Ele_Data = public_data.getDemData(x, y)
            Lon_data, Lat_data = public_data.getLonLat(x, y)  # 经纬度数据
            GeoTransform =(x,GT[1],GT[2],y,GT[4],GT[5])

            site_num = []
            for i in site:
                column, row = public_data.WGS2NUM(i[1], i[2], x, y)
                if 0 < column < 1200 and 0 < row < 1200:  # 如果站点在这一景数据中
                    site_num.append([column, row, i[0], i[1], i[2]])
            print('{}内共有观测站{}个'.format(block_num,len(site_num)))

            if len(site_num) == 0:
                write = False
            elif len(site_num) != 0:
                write = True

            for date in date_list:

                tem_csv = copy.deepcopy(site_num)
                time = re.search(r'(\d*)-(\d*)-(\d*)', date)
                for i in tem_csv:  # 写入年月日数据
                    i.append(time.group(1))
                    i.append(time.group(2))
                    i.append(time.group(3))

                if os.path.isfile('result\\SIN\\{}_{}_Average_SIN.tif'.format(block_num,date)):
                    print('{}   {}平均地温已经计算过'.format(block_num,date))
                else:
                    self.count_day(date,block_num,Ele_Data,Lon_data,Lat_data,GeoTransform,tem_csv,write)


class Splicing:

    def __init__(self,date,block,dir_data,dir_out,filename,Nodata = 0):
        self.date     = date
        self.block    = block
        self.dir_data = dir_data
        self.dir_out  = dir_out
        self.filename = filename
        self.Nodata   = Nodata

    def get_extent(self,fn):

        ds = gdal.Open(fn)
        rows = ds.RasterYSize
        cols = ds.RasterXSize
        # 获取图像角点坐标
        gt = ds.GetGeoTransform()
        minx = gt[0]
        maxy = gt[3]
        maxx = gt[0] + gt[1] * cols
        miny = gt[3] + gt[5] * rows

        return (minx, maxy, maxx, miny)

    def splicing(self,date):

        in_files =[]
        for block_num in self.block:
            in_files.append('{}\\{}_{}_Average_SIN.tif'.format(self.dir_data,block_num,date))

        minX, maxY, maxX, minY= self.get_extent(in_files[0])
        for fn in in_files[1:]:
            minx, maxy, maxx, miny= self.get_extent(fn)
            minX = min(minX, minx)
            maxY = max(maxY, maxy)
            maxX = max(maxX, maxx)
            minY = min(minY, miny)

        # 获取输出图像的行列数
        in_ds = gdal.Open(in_files[0])
        gt = in_ds.GetGeoTransform()
        rows = int((maxY - minY) / abs(gt[5]))
        cols = int((maxX - minX) / abs(gt[1]))

        # 创建输出图像
        driver = gdal.GetDriverByName('gtiff')
        out_ds = driver.Create('{}\\{}_{}_SIN.tif'.format(self.dir_out,self.filename,date), cols, rows,1,gdal.GDT_Float64)
        out_ds.SetProjection(in_ds.GetProjection())
        out_band = out_ds.GetRasterBand(1)
        gt = list(in_ds.GetGeoTransform())
        gt[0], gt[3] = minX, maxY
        out_ds.SetGeoTransform(gt)
        for fn in in_files:
            in_ds = gdal.Open(fn)
            trans = in_ds.GetGeoTransform()
            x = int(abs(trans[0]-gt[0])/abs(gt[1]))
            y = int(abs(trans[3]-gt[3])/abs(gt[5]))

            data = in_ds.GetRasterBand(1).ReadAsArray()
            out_band.WriteArray(data, x, y)

        out_band.SetNoDataValue(self.Nodata)

        del in_ds, out_band, out_ds

    def getEveryDay(self,begin_date, end_date):
        # 获取范围内所有的日期

        date_list = []
        begin_date = datetime.datetime.strptime(begin_date, "%Y-%m-%d")
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")
        while begin_date <= end_date:
            date_str = begin_date.strftime("%Y-%m-%d")
            date_list.append(date_str)
            begin_date += datetime.timedelta(days=1)

        return date_list

    def main(self):

        time = self.getEveryDay(self.date[0],self.date[1])
        total = len(time)
        progress = progress_bar(total,'拼接中')
        now = 0
        progress.show_now(now)

        for i in time:
            now += 1

            self.splicing(i)
            SHOW = data_show(1)
            SHOW.ReProjection('{}\\{}_{}_SIN.tif'.format(self.dir_out,self.filename,i),'{}\\{}_{}_WGS84.tif'.format(self.dir_out,self.filename,i),4326)
            progress.show_now(now)

        print('')
