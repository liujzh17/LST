#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Feb 19 02:34:17 2020

@author: bincao
"""

from ModisLST import interpolation
import matplotlib.pyplot as plt


# ==== SETTING-UP =============================================================
        
dir_data = '/Users/bincao/OneDrive/GitHub/LST/data/Tibet'


# ==== INTERPOLATION ==========================================================

INT = interpolation(dir_data)

flist = INT.getFile()
# print(flist)
lstv = INT.dataFilter(flist[2])


# show something....
import numpy.ma as ma
mask = lstv == 9999
v = ma.array(lstv, mask = mask)
plt.imshow(v)