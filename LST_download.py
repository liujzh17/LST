# !/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on : 2020/4/9 12:34

@Author : jz liu
'''
# ============ HOW TO USE download1 ===============================================
'''

    1)Adapt the settings like example1
    
'''
# ================= example1 ======================================================
'''
from LST_download import download1

dir_out  = 'data'
username = '1572524747'
password = 'Aa111111'
time     = ['2019-01-01','2019-01-02']
location = ['70.0','30.0','90.0','20.0']
product  = 'MOD11A1--6'

tryOne = download1(dir_out,username,password,time,location,product)
tryOne.main()
'''
# ============ HOW TO USE download2 ===============================================
'''
    1)Get url files you need from Earthdata by search "MOD11A1" or "MYD11A1".
    
    2)Adapt the settings like example2
'''
# ============ example2 ============================================================
'''
from LST_download import download2

urlfile  = 'data/urlfile.txt'
dir_out  = 'data'
username = '1572524747'
password = 'Aa111111'

tryOne = download2(urlfile,dir_out,username,password)
tryOne.main()
'''

import re
import os
import requests
import platform
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class download1():

    def __init__(self,dir_out,username,password,time,location,product='MOD11A1--6'):
        '''
        :param dir_out:  directory to save the download file
        :param username: username of Earthdata
        :param password: password of Earthdata
        :param time:     [time_start({}-{}-{}),time_end({}-{}-{})]
        :param location: [lat[rightup],lon[rightup],lat[leftdown],lon[leftdown]]
        :param product:  name of product

        '''
        if product == 'MOD11A1--6':
            self.filename = 'MODIS_MOD11A1_V006'
        elif product == 'MYD11A1--6':
            self.filename = 'MODIS_MYD11A1_V006'
        else:
            print('这个程序是用来下载mod11和myd11两个数据集，理论上也可以下载其他数据集，'
                  '但是输出地址可能会重复导致数据覆写的情况，如果仍要继续，请删除源代码中的第74行')
            raise
        self.dir_out  = dir_out
        self.username = username
        self.password = password
        self.time     = '{}..{}' .format(time[0],time[1])
        self.location = '{},{},{},{}'.format(location[0],location[1],location[2],location[3])
        self.product  = product

        print('正在下载{}'.format(product))

    def build_url(self):
        # Create url
        # return url of objective

        url = 'https://ladsweb.modaps.eosdis.nasa.gov/search/order/4/{}/{}/DB/{}'\
              .format(self.product,self.time,self.location)

        return url

    def check_OS(self):
        # check what OS you are using

        sys = platform.system()

        return sys

    def get_web(self,url):
        # Create a web driver of chrome which after loading
        # note: please close driver after useing

        chrome_options = Options()
        chrome_options.add_argument('--headless')

        sys = self.check_OS()

        if sys == 'Windows':
            driver = webdriver.Chrome(options=chrome_options,
                                      executable_path='webdriver\\chromedriver.exe')
        elif sys == 'Linux':
            driver = webdriver.Chrome(options=chrome_options,
                                      executable_path='webdriver\\chromedriver_linux')
        elif sys == 'Mac':
            driver = webdriver.Chrome(options=chrome_options,
                                      executable_path='webdriver\\chromedriver_mac')
        driver.get(url)

        while True:
            try:
                driver.find_element_by_xpath('//*[@id="tab4FilesTable"]/tbody')
                break

            except:
                pass

        return driver

    def build_url_dic(self,driver):
        # Create a dic of every objective
        '''
        :param driver: webdriver
        :return: {h??v?? : [ [date1,url1] , [date2,url2],...,[date,url] ] }
        '''

        k = 1
        catalog = {}

        while True:

            i = 0
            k += 1
            while True:
                i += 1

                try:
                    test = '//*[@id="tab4FilesTable"]/tbody/tr[{}]'.format(i)
                    driver.find_element_by_xpath(test)
                except:
                    break

                xp_id = '{}/td[1]'.format(test)
                xp_date = '{}/td[3]/div'.format(test)
                xp_url = '{}/td[4]/div/a'.format(test)

                while True:
                    try:
                        ID = driver.find_element_by_xpath(xp_id).get_attribute('textContent')
                        ID = re.search(r'h(\d*)v(\d*)', ID).group()
                        date = driver.find_element_by_xpath(xp_date).get_attribute('textContent')
                        date = re.search(r'(\d*)-(\d*)-(\d*)', date).group()
                        data_url = driver.find_element_by_xpath(xp_url).get_attribute('href')
                        break

                    except:
                        pass

                try:
                    x = catalog[ID]
                    catalog[ID].append([date, data_url])
                except:
                    catalog[ID] = []
                    catalog[ID].append([date, data_url])

            try:
                driver.find_element_by_xpath('//*[@id="tab4FilesTable_paginate"]/span/a[{}]'.format(k)).click()

            except:
                break

        driver.close()

        for name in catalog:
            break
        print('block：{}   day：{}'.format(len(catalog),len(catalog[name])))

        return catalog

    def check_dir(self):
        '''
        Create Floder like this if it don't

        data/h00v00/aqua/????-??-??.hdf
                         .
                         .
                    terra/????-??-??.hdf
                         .
                         .
             .
             .
             .
             h01v00/aqua/????-??-??.hdf
                         .
                         .
                    terra/????-??-??.hdf
                         .
                         .
             .
             .
             .
             h35v17/aqua/????-??-??.hdf
                         .
                         .
                    terra/????-??-??.hdf
                         .
                         .

        '''

        for h in range(36):
            for v in range(18):
                for i in ('auqa','terra'):
                    try:
                        os.makedirs(r'data/h{:0>2d}v{:0>2d}/{}'.format(h,v,i))
                    except:
                        pass

        print('目录校正完成')

    def download(self,dic):
        # download all file
        session = SessionWithHeaderRedirection(self.username,self.password)

        for i in dic:
            for k in dic[i]:
                if os.path.isfile(r"{}/{}_{}_{}.hdf".format(self.dir_out,self.filename,i,k[0])):
                    print('{} {} {}已经存在'.format(self.product,i,k[0]))
                else:
                    data = session.get(k[1], stream=True)
                    print(data.status_code, '\t', i)
                    with open(r"{}/{}_{}_{}.hdf".format(self.dir_out,self.filename,i,k[0]),"wb") as code:
                        code.write(data.content)
                    print('{} {} {}下载完成'.format(self.product,i,k[0]))
                    code.close()

        print('下载完成')

    def main(self):
        # start running

        url = self.build_url()

        driver  = self.get_web(url)
        catalog = self.build_url_dic(driver)

        self.download(catalog)

class download2():

    def __init__(self,urlfile,dir_out,username,password):

        self.urlfile  = urlfile
        self.dir_out  = dir_out
        self.username = username
        self.password = password

    def build_url_dic(self):
        # Create a dic of every objective

        catalog = {}

        with open(self.urlfile) as f:
            urllist = f.read().splitlines()
            for url in urllist:
                block   = re.search(r'h(\d*)v(\d*)', url).group()
                product = re.search(r'M(\D?)D11A1', url).group()
                ID      = 'MODIS_{}_V006_{}'.format(product,block)
                time    = re.search(r'(\d{4}).(\d{2}).(\d{2})', url)
                time_id = '{}-{}-{}'.format(time.group(1),time.group(2),time.group(3))


                try:
                    x = catalog[ID]
                    catalog[ID].append([time_id, url])
                except:
                    catalog[ID] = []
                    catalog[ID].append([time_id, url])

        return catalog

    def download(self,dic):
        # download all file
        session = SessionWithHeaderRedirection(self.username, self.password)

        for i in dic:
            for k in dic[i]:
                if os.path.isfile(r"{}/{}_{}.hdf".format(self.dir_out, i, k[0])):
                    print('{} {} 已经存在'.format(i, k[0]))
                else:
                    data = session.get(k[1], stream=True)
                    print(data.status_code, '\t', i)
                    with open(r"{}/{}_{}.hdf".format(self.dir_out, i, k[0]), "wb") as code:
                        code.write(data.content)
                    print('{} {} 下载完成'.format(i, k[0]))
                    code.close()

        print('下载完成')

    def main(self):
        # start running

        catalog = self.build_url_dic()
        self.download(catalog)



class SessionWithHeaderRedirection(requests.Session):
    AUTH_HOST = 'urs.earthdata.nasa.gov'

    def __init__(self, username, password):

        super().__init__()

        self.auth = (username, password)

    # Overrides from the library to keep headers when redirected to or from

    # the NASA auth host.

    def rebuild_auth(self, prepared_request, response):

        headers = prepared_request.headers

        url = prepared_request.url

        if 'Authorization' in headers:

            original_parsed = requests.utils.urlparse(response.request.url)

            redirect_parsed = requests.utils.urlparse(url)

            if (original_parsed.hostname != redirect_parsed.hostname) and redirect_parsed.hostname != self.AUTH_HOST and original_parsed.hostname != self.AUTH_HOST:
                del headers['Authorization']

        return







