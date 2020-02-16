from pyhdf.SD import SD,SDC

class QC:
    def __init__(self,name):
        self.getQC=SD(name).select('QC_Day').get()
    def GetData(self,rawQC):
        data=[]
        for i in rawQC:
            for k in i:
                k = bin(k)[2:]
                if len(k) != 8:
                    k = "%08d" % int(k)
                data.append(k)
        return data


