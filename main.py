'''
    第一版完成于2020/2/14 可以完成全部流程，生成时间插值图和最终空间插值图，
    并记录两次过程的精度

    尚存在的问题包括：
        1.TPS的训练点的选取比较粗糙
        2.每天只选取了一个时间的影像，还未完善每天四幅影像合成
        3.这个版本最终的图像保留了出现异常大或异常小值的区域，因为不完全清楚
          这些区域是因为地形地物影响还是插值出现错误，暂时保留此问题
        4.算法没有经过精简，每生成一天的图像预计需要1小时左右的时间
        5.由于只是测试2020/1/5日的影像修复，关于源数据的路径只是记录测试数据地址，
          没有优化为自动匹配，还不能批量修复多个影像
'''



from pyhdf.SD import SD,SDC
import image_output
import Qcheck
import os
import lwr
import traceback
import TPS


def main():

    #准备一个临时数据用以储存回归所需数据
    tem_data=[]

    #调入所有的数据
    path = r'data\\Tibet'
    quit=1
    for filename in os.listdir(path):
        if quit==1 or quit==7:
            pass
        else:
            HDF_FILR_URL =path+'\\\\'+filename

            #整理温度数据
            file = SD(HDF_FILR_URL)
            EV_1KM_Emissive = file.select('LST_Day_1km').get()
            data=[]
            for i in EV_1KM_Emissive:
                for k in i:
                    if k==0:
                        k=round(k,2)
                    else:
                        k = k * 0.02 - 273.15
                        k = round(k, 2)
                    data.append(k)



            #整理质量指数数据
            name=HDF_FILR_URL
            QC = Qcheck.QC(name)
            Qcdata = QC.GetData(QC.getQC)

            #质量筛选(<=3K)
            for i in range(len(Qcdata)):
                if Qcdata[i][6:8] == '11':
                    data[i] = 0
            tem_data.append(data)      #把整理过的数据放进临时数据
        quit+=1

    #时间序列补充
    new_data=[]
    Alwr = 0
    Accuracy_lwr = []
    for i in range(len(tem_data[2])):
        dataSet = []
        Labels = []
        if tem_data[2][i] != 0:
            for k in range(5):
                if tem_data[k][i]==0:
                    pass
                else:
                    if k==3:
                        pass
                    else:
                        dataSet.append([1, k+1])
                        Labels.append(tem_data[k][i])
            if dataSet==[] or len(dataSet)==1:
                pass
            else:
                Hat = lwr.lwlr([1,3], dataSet, Labels)
                if Hat==None:
                    pass
                else:
                    Hat = round(float(Hat), 2)
                    Alwr=abs(Hat-tem_data[2][i])
                    Accuracy_lwr.append(Alwr)
            Hat=tem_data[2][i]
        else:
            for k in range(5):
                if tem_data[k][i]==0:
                    pass
                else:
                    dataSet.append([1, k + 1])
                    Labels.append(tem_data[k][i])
            if dataSet==[] or len(dataSet)==1:
                Hat=-70.00
            else:
                Hat = lwr.lwlr([1, 3], dataSet, Labels)
                if Hat==None:
                    Hat=-70.00
            Hat = round(float(Hat), 2)
        new_data.append(Hat)

    #时间序列补充精度评价
    mean=sum(Accuracy_lwr)/len(Accuracy_lwr)
    f=open('时间插值精度.txt','w')
    f.write('最大值:{}\n最小值：{}\n平均值：{}'.format(max(Accuracy_lwr),min(Accuracy_lwr),mean))
    f.close()


    #保存文件
    f=open('temporal.txt','w')
    f.write(str(new_data))
    f.close()

    #出图
    new_data1=image_output.correct(new_data)
    image=image_output.ImageMake(1200,1200,new_data1)
    image.OutPut(image.data,color='twilight')

    #空间序列补充(第一次插值，不记录精度评价）
    band31_data=TPS.band31_lwr()
    fin_data1=TPS.tps(new_data,band31_data)
    #空间序列补充(第二次插值，记录精度评价）
    fin_data=TPS.tps(fin_data1,band31_data,QA=True)

    #出图
    fin_data2=image_output.correct(fin_data)
    image=image_output.ImageMake(1200,1200,fin_data2)
    image.OutPut(image.data,color='twilight')

    #保存文件
    f=open('spatial.txt','w')
    f.write(str(fin_data))
    f.close()

if __name__ == "__main__":
    try:
        main()
    except:
        traceback.print_exc()



