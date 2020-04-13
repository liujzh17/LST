# !/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on : 2020/4/9 12:34

@Author : jz liu
'''
#现在的下载方法在登陆时只有几次可以登陆下载到数据，还不能投入实际使用！！！
# ================= example ======================================================
'''
from LST_download import download

dir_out  = 'data'
username = '1572524747'
password = 'Aa111111'
time     = ['2019-01-01','2019-01-02']
location = ['70.0','30.0','90.0','20.0']
product  = 'MOD11A1--6'

tryOne = download(dir_out,username,password,time,location,product)
url    = tryOne.build_url()

tryOne.check_dir()

driver  = tryOne.get_web(url)
catalog = tryOne.build_url_dic(driver)

tryOne.download(catalog)
'''


import re
import os
import urllib.request
from selenium import webdriver
from http.cookiejar import CookieJar
from selenium.webdriver.chrome.options import Options


class download():

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
            self.satellite = 'terra'
        elif product == 'MYD11A1--6':
            self.satellite = 'aqua'
        else:
            print('这个程序是用来下载mod11和myd11两个数据集，理论上也可以下载其他数据集，'
                  '但是输出地址可能会重复导致数据覆写的情况，如果仍要继续，请删除源代码中的第57行')
            raise
        self.server   = "https://urs.earthdata.nasa.gov"
        self.dir_out  = dir_out
        self.username = username
        self.password = password
        self.time     = '{}..{}' .format(time[0],time[1])
        self.location = '{},{},{},{}'.format(location[0],location[1],location[2],location[3])
        self.product  = product

        print('正在下载{}'.format(product))

    def build_url(self):
        #Create url
        #return url of objective

        url = 'https://ladsweb.modaps.eosdis.nasa.gov/search/order/4/{}/{}/DB/{}'\
              .format(self.product,self.time,self.location)

        return url

    def get_web(self,url):
        #Create a web driver of chrome which after loading
        #note: please close driver after useing

        chrome_options = Options()
        chrome_options.add_argument('--headless')

        driver = webdriver.Chrome(options=chrome_options,
                                  executable_path='chromedriver.exe')
        driver.get(url)

        while True:
            try:
                driver.find_element_by_xpath('//*[@id="tab4FilesTable"]/tbody')
                break

            except:
                pass

        return driver

    def build_url_dic(self,driver):
        #Create a dic of every objective
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

    def passwordManager(self):
        # Create a password manager to deal with the 401 reponse that is
        # returned from Earthdata Login

        password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
        password_manager.add_password(None, self.server,
                                      self.username, self.password)

        return password_manager

    def opener(self):

        password_manager = self.passwordManager()

        # Create a cookie jar for storing cookies. This is used to store and
        # return the session cookie given to use by the data server (otherwise
        # it will just keep sending us back to Earthdata Login to authenticate).
        # Ideally, we should use a file based cookie jar to preserve cookies
        # between runs. This will make it much more efficient.
        cookie_jar = CookieJar()

        opener = urllib.request.build_opener(
            urllib.request.HTTPBasicAuthHandler(password_manager),
            urllib.request.HTTPCookieProcessor(cookie_jar))
        urllib.request.install_opener(opener)


    def dataBody(self, url):
        # Create and submit the request and get the data body.
        # There are a wide range of exceptions that can be thrown here,
        # including HTTPError and URLError. These should be caught and handled.

        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request, timeout=60)
        body = response.read()

        return body


    def exportFile(self,block,filename, body):
        # Save file to working directory

        file_ = open(r"{}/{}/{}/{}.hdf".format(self.dir_out,block,self.satellite,filename), 'wb')
        file_.write(body)
        file_.close()


    def breakin(self, url,block,filename):
        # Rob one file

        self.opener()  # Install all the handlers.
        body = self.dataBody(url)
        self.exportFile(block,filename, body)

    def download(self,dic):

        for i in dic:
            for k in dic[i]:
                if os.path.isfile(r"{}/{}/{}/{}.hdf".format(self.dir_out,i,self.satellite,k[0])):
                    print('{} {} {}已经存在'.format(self.product,i,k[0]))
                else:
                    self.breakin(k[1],i,k[0])
                    print('{} {} {}下载完成'.format(self.product,i,k[0]))

        print('下载完成')

'''
    def download_bate(self,dic):
        #this method use to success,the reason why fail now are not clear
        #hold this method for solving the problem of login with 'requests' in tht future
        
        post_url  = 'https://urs.earthdata.nasa.gov/login'
        post_data = {'username': self.username, 'password': self.password}
        headers   = {
                     'User-Agent':'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36'
                    }
        session   = requests.session()
        session.post(post_url,data=post_data,headers=headers)

        for i in dic:
            for k in dic[i]:
                data = session.get(k[1],headers=headers)
                if os.path.isfile(r"{}/{}/{}/{}.hdf".format(self.dir_out,i,self.satellite,k[0])):
                    print('{} {} {}已经存在'.format(self.product,i,k[0]))
                else:
                    with open(r"{}/{}/{}/{}.hdf".format(self.dir_out,i,self.satellite,k[0]),"wb") as code:
                        code.write(data.content)
                    print('{} {} {}下载完成'.format(self.product,i,k[0]))
                    code.close()

        print('下载完成')

'''








