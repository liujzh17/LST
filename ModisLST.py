#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 19 02:35:15 2020

@author: bincao
"""


import image_output
import Qcheck

import lwr
import traceback
import TPS

import numpy as np

from pyhdf.SD import SD, SDC
from os import listdir, path



class interpolation(object):
    
    def __init__(self, dir_data):
        self.dir = dir_data
        
    def getFile(self):
        # get all the lst files
        
        flist = np.sort(listdir(self.dir))
        
        return flist
    
    def int2bin(self, intv):
        
        intv = [bin(vi) for vi in intv]
        
        return intv
        
    def getVarName(self, DayNightFlag, var):
        # get var name of Modis HDF
        
        if var == 'lst':
            varName = 'LST_{}_1km'.format(DayNightFlag)
        elif var == 'qc':
            varName = 'QC_{}'.format(DayNightFlag)
        
        return varName
    
    def lstScale(self, lstv, fillV = 9999):
        # from [K] to [˚C]
        
        lstv = lstv * 0.02 - 273.15
        lstv[lstv == -273.15] = fillV # [BC: 0 是无值对吗？]
        
        return lstv
    
    def dataFilter(self, lstf, DayNightFlag = 'Day'):
        # remove data with error > 3K
        
        hdf = SD(path.join(self.dir, lstf))
        lstv  = hdf.select(self.getVarName(DayNightFlag, 'lst')).get()
        lstv = self.lstScale(lstv)
        
        QC  = hdf.select(self.getVarName(DayNightFlag, 'qc')).get()
        QC = [bin(vi)[-2::] for vi in QC.reshape(QC.size)]
        mask = (np.asarray(QC) == '00').reshape(lstv.shape)
        lstv[mask] = 9999        
        
        return lstv