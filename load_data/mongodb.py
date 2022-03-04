#encoding:utf-8
import sys

#verion1: get all companies data from tushare and store them in Mongodb
import pymongo
import datetime
import tushare as ts
import time
import json
import pandas as pd
from collections import OrderedDict
import pytz
import types 
import requests
from io import BytesIO, StringIO
import os
import click
import re
from os import listdir
from os.path import isfile, join
from os import walk
import gc

from pandas import DataFrame



class LoadDataCVS:

    basedir="E:/data_new"
    stockdata=basedir+"/stock_data"
    indexdata=basedir+"/index_data"

    #treasurvity 
    in_package_data = range(2002, 2018)
    DONWLOAD_URL = "http://yield.chinabond.com.cn/cbweb-mn/yc/downYearBzqx?year=%s&&wrjxCBFlag=0&&zblx=txy&ycDefId=%s"
    YIELD_MAIN_URL =  'http://yield.chinabond.com.cn/cbweb-mn/yield_main'
    #
    #'http://yield.chinabond.com.cn/cbweb-mn/yield_main'
    
    #'#http://yield.chinabond.com.cn/cbweb-mn/yield_main?locale=zh_CN','http://yield.chinabond.com.cn/cbweb-mn/yield_main?locale=zh_CN'


    
    def __init__(self,Ip,port):
        self.ip=Ip
        self.port=port

    ## connect to the data base
    def Conn(self):
        self.client = pymongo.MongoClient(self.ip,self.port)
        self.connection=self.client.stock #storage stock information
        self.index=self.client.index #storage index
        self.pool=self.client.pool  #storate pool
        self.treasure=self.client.treasure
        self.minute_stock = self.client.minute_stock
        self.minute_index = self.client.minute_index
        #print self.connection.collection_names()
        #print self.index.collection_names()
        #print self.pool.collection_names()
    def Close(self):
        self.client.close()
        
        
    #store data information into database, do not always call this
    def storagedaily(self):
        #get the filelist
        onlyfiles = [ f for f in listdir(self.stockdata) if isfile(join(self.stockdata,f)) ]
        #read from using pandas
        for f in onlyfiles:
            df = pd.read_csv(self.stockdata+"/"+f)
            #print df.head()
            s=f.split('.')
            name = s[0][2:8]
            #print name
            records = json.loads(df.T.to_json()).values()
            for row in records:
                row['date'] = datetime.datetime.strptime(row['date'], "%Y-%m-%d")
                #print row
                #raw_input()
            print (name)
            self.connection[name].insert_many(records)
            
    #store index information into database,do not always call this
            
    def storageindex(self):
        #get the filelist
        onlyfiles = [ f for f in listdir(self.indexdata) if isfile(join(self.indexdata,f)) ]
        #read from using pandas
        for f in onlyfiles:
            df = pd.read_csv(self.indexdata+"/"+f)
            s=f.split('.')
            name = s[0][2:8]
            records = json.loads(df.T.to_json()).values()
            for row in records:
                row['date'] = datetime.datetime.strptime(row['date'], "%Y-%m-%d")
            print (name)
            self.index[name].insert_many(records)
            
    
    
    #storage stock pool into database
    def storagepool(self):
        #storage zz500
        df=ts.get_zz500s()
        self.pool['zz500'].insert_many(json.loads(df.to_json(orient='records')))
        #hs300
        df=ts.get_hs300s()
        self.pool['hz300'].insert_many(json.loads(df.to_json(orient='records')))
        #zh50
        df=ts.get_sz50s()
        self.pool['sz'].insert_many(json.loads(df.to_json(orient='records')))
        #st
        df=ts.get_st_classified()
        self.pool['st'].insert_many(json.loads(df.to_json(orient='records')))
        
        
    
        
    #get the particular stock list from data base
    def getstocklist(self,kind):
        ret=[]
        if kind=="hs300":
            ret.extend(t['code'] for t in self.pool['hz300'].find())
        if kind =="zz500":
            ret.extend(t['code'] for t in self.pool['zz500'].find())
        if kind=='sz50':
            ret.extend(t['code'] for t in self.pool['sz'].find())
        if kind =='st':
            ret.extend(t['code'] for t in self.pool['st'].find())
        if kind == 'all':
            ret.extend(t['codes'] for t in self.pool['all'].find())
        return ret 
        
        #get daily stock information from database
        #return dataframe which contains the information we set in the parameters

    def getstockdaily(self,code,start='2000-01-01',end='2099-01-01'):
        total=[]
        startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        enddate=datetime.datetime.strptime(end, "%Y-%m-%d")
        series={"date":[],"open":[],"close":[],"high":[],"low":[],"volume":[],"prices":[],"change":[],"code":[]}
        #now_time=time.time()
        #print self.connection[code].find({"date": {"$gte": startdate,"$lt":enddate}}).sort("date")
        #new_time = time.time()
        #print new_time - now_time
        #tt = self.connection[code].find({},{'_id':0,'date':1}).sort('date',-1)
        #print tt[0]['date']
        #raw_input()
        tt = self.connection[code].find({"date": {"$gte": startdate,"$lte":enddate}}).sort("date")
        for stockdaily in tt:
            series["date"].append(stockdaily["date"])
            series["open"].append(stockdaily["open"])
            series["close"].append(stockdaily["close"])
            series["high"].append(stockdaily["high"])
            series["low"].append(stockdaily["low"])
            series["volume"].append(stockdaily["volume"])
            series["prices"].append(stockdaily["adj_factor"])
            series["change"].append(stockdaily["change"])
            series["code"].append(stockdaily["code"])
        #pp=time.time() 
        del tt 
        gc.collect()
        totaldata=zip(series['open'],series['high'],series['low'],series['close'],series['volume'],series["prices"],series["change"],series["code"])
        df = pd.DataFrame(data=list(totaldata),index=series["date"],columns = ['open','high','low','close','volume','prices','change',"code"])
        try:
            df['price'] = (df['close']*df['prices'])/(list(df['prices'])[-1])
            df =  df[['open','high','low','close','volume','price','change',"code"]]
            #print df.drop_duplicates()
            #raw_input()
            return df.drop_duplicates()
        except:
            df.columns = ['open','high','low','close','volume','price','change',"code"]
            return df.drop_duplicates()
            
            
    def getstockminute(self,code,start,end):
        startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        enddate=datetime.datetime.strptime(end, "%Y-%m-%d")
        series={"date":[],"open":[],"close":[],"high":[],"low":[],"volume":[],"prices":[],"change":[],"code":[]}
        tt_date = '1991-01-01'
        tt = self.minute_stock[code].find({"date": {"$gte": startdate,"$lte":enddate}}).sort("date")
        for stockdaily in tt:
            if tt_date != str(stockdaily["date"])[:10]:
                time_day = datetime.datetime.strptime(str(stockdaily['date'])[:10], "%Y-%m-%d")
                tt =self.connection[code].find({"date": {"$gte":time_day ,"$lte":time_day}})[0]
                tt_date = str(stockdaily["date"])[:10]
            series["date"].append(stockdaily["date"])
            series["open"].append(stockdaily["open"])
            series["close"].append(stockdaily["close"])
            series["high"].append(stockdaily["high"])
            series["low"].append(stockdaily["low"])
            series["volume"].append(stockdaily["vol"])
            series["prices"].append(tt["adj_factor"])
            series["change"].append(stockdaily["p_change"])
            series["code"].append(stockdaily["code"])
        #pp=time.time
        del tt
        gc.collect()
        totaldata=zip(series['open'],series['high'],series['low'],series['close'],series['volume'],series["prices"],series["change"],series["code"],series['date'])

        df = pd.DataFrame(data=list(totaldata),index=series["date"],columns = ['open','high','low','close','volume','prices','change',"code",'date'])
        df['change']= df['change']/100
        df['volume'] = df['volume']*100
        for factor in ['open','close','high','low','prices']:
            df[factor] = [float("%.2f"%i) for i in list(df[factor])]
        df = df.drop_duplicates(subset=['date'])
        #df.to_csv('E:\\stock_%sdatashujuqingkaung.csv'%list(df['code'])[0])
        try:
            df['price'] = (df['close']*df['prices'])/(list(df['prices'])[-1])
            df =  df[['open','high','low','close','volume','price','change',"code"]]
            return df
        except:
            #df.drop_duplicates().fillna(method='pad').to_csv('E:\\stock_datashujuqingkaung.csv')
            df.columns = ['open','high','low','close','volume','price','change',"code"]
            return df


    
    def getBenchamark(self,code,start,end):
        #if it is timestamp type
        startdate=start
        enddate=end
        #print u'这里',start,end
        if type(start) is types.StringType:
            startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        if type(end) is types.StringType:
            enddate=datetime.datetime.strptime(end, "%Y-%m-%d")           
        series={"date":[],"change":[]}
        for stockdaily in self.index[code].find({"date": {"$gte": startdate,"$lte":enddate}}).sort("date"):
            series["date"].append(stockdaily["date"])
            series["change"].append(stockdaily["change"])
        df=pd.Series(data=series["change"],index=series["date"])
        return df.sort_index().tz_localize('UTC')

    def getindexdaily(self,code,start,end):
        total=[]
        startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        enddate=datetime.datetime.strptime(end, "%Y-%m-%d")
        series={"date":[],"open":[],"close":[],"high":[],"low":[],"volume":[]}
        
        for stockdaily in self.index[code].find({"date": {"$gte": startdate,"$lt":enddate}}).sort("date"):
            series["date"].append(stockdaily["date"])
            series["open"].append(stockdaily["open"])
            series["close"].append(stockdaily["close"])
            series["high"].append(stockdaily["high"])
            series["low"].append(stockdaily["low"])
            series["volume"].append(stockdaily["volume"])
            
        totaldata=zip(series['date'],series['open'],series['close'],series['high'],series['low'],series['volume'])
        df = pd.DataFrame(list(totaldata))
        df.columns = ['date','open','close','high','low','volume']
        #print (df.head())
        #df.index=df.date
        return df
        
    def getindexminute(self,code,start,end):
        total=[]
        startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        enddate=datetime.datetime.strptime(end, "%Y-%m-%d")
        series={"date":[],"open":[],"close":[],"high":[],"low":[],"volume":[]}
        
        for stockdaily in self.minute_index[code].find({"date": {"$gte": startdate,"$lt":enddate}}).sort("date"):
            series["date"].append(stockdaily["date"])
            series["open"].append(stockdaily["open"])
            series["close"].append(stockdaily["close"])
            series["high"].append(stockdaily["high"])
            series["low"].append(stockdaily["low"])
            series["volume"].append(stockdaily["vol"])
            
        totaldata=zip(series['date'],series['open'],series['close'],series['high'],series['low'],series['volume'])
        df = pd.DataFrame(list(totaldata))
        df.index=df.date
        return df.drop_duplicates()
        



    def get_data(self):

        in_package_data = range(2002, 2019)
        print (in_package_data)
        cur_year = datetime.datetime.now().year
        # download new data
        '''
        to_downloads = range(last_in_package_data + 1, cur_year + 1)
        print to_downloads
        raw_input()

        # frist, get ycDefIds params
        response = requests.get(self.YIELD_MAIN_URL)

        matchs = re.search(r'\?ycDefIds=(.*?)\&', response.text)
        ycdefids = matchs.group(1)
        assert (ycdefids is not None)

        fetched_data = []
        for year in to_downloads:
            print('Downloading from ' + self.DONWLOAD_URL % (year, ycdefids))
            response = requests.get(self.DONWLOAD_URL % (year, ycdefids))
            fetched_data.append(BytesIO(response.content))

        # combine all data'''

        basedir = os.path.join(os.path.dirname(__file__), "xlsx")

        last_in_package_data = max(in_package_data)
        dfs = [
            pd.read_excel(os.path.join(basedir, "%d.xlsx" % i))
            for i in in_package_data
        ]

        '''
        for memfile in fetched_data:
            dfs.append(pd.read_excel(memfile))
        '''
        return pd.concat(dfs)

    def get_pivot_data(self):

        df = self.get_data()
        return df.pivot(index=u'日期', columns=u'标准期限(年)', values=u'收益率(%)')



    def insert_zipline_treasure_format(self):
        self.treasure['treasure'].drop()
        pivot_data = self.get_pivot_data()
        #print pivot_data.tail()
        #raw_input()

        frame=pivot_data[[0.08,0.25,0.5,1,2,3,5,7,10,20,30]]
        frame['Time Period']=frame.index
        #print frame.head()
        frame['Time Period']=  frame['Time Period'].astype('str') # [str(i) for i in list(frame['Time Period'])]#
        frame.columns=['1month', '3month','6month', '1year', '2year', '3year', '5year', '7year', '10year', '20year', '30year','Time Period']
        records = json.loads(frame.T.to_json()).values()
        for row in records:
            temp=row['Time Period']
            temp=temp.split('T')[0]
            row['Time Period'] = datetime.datetime.strptime(temp, "%Y-%m-%d")

        self.treasure['treasure'].insert_many(records)
       

    def read_treasure_from_mongodb(self,start,end):

        startdate=start
        enddate=end
        series={"Time Period":[],"1month":[],"3month":[],"6month":[],"1year":[],"2year":[],"3year":[],"5year":[],"7year":[],"10year":[],"20year":[],"30year":[]}
        if type(start) is types.StringType:
            startdate = datetime.datetime.strptime(start, "%Y-%m-%d")
        if type(end) is types.StringType:
            enddate=datetime.datetime.strptime(end, "%Y-%m-%d")
        for treasuredaily in self.treasure['treasure'].find({"Time Period": {"$gte": startdate,"$lt":enddate}}).sort("date"):
            series["Time Period"].append(treasuredaily["Time Period"])
            series["1month"].append(treasuredaily["1month"])
            series["3month"].append(treasuredaily["3month"])
            series["6month"].append(treasuredaily["6month"])
            series["1year"].append(treasuredaily["1year"])
            series["2year"].append(treasuredaily["2year"])
            series["3year"].append(treasuredaily["3year"])
            series["5year"].append(treasuredaily["5year"])
            series["7year"].append(treasuredaily["7year"])
            series["10year"].append(treasuredaily["10year"])
            series["20year"].append(treasuredaily["20year"])
            series["30year"].append(treasuredaily["30year"])
        totaldata=zip(series["1month"],series["3month"],series["6month"],series["1year"],series["2year"],series["3year"],series["5year"],series["7year"],series["10year"],series["20year"],series["30year"])
        df = pd.DataFrame(data=list(totaldata),index=series["Time Period"],columns = ['1month', '3month','6month', '1year', '2year', '3year', '5year', '7year', '10year', '20year', '30year'])
        return df.sort_index().tz_localize('UTC')

    def storageStockName(self):
        totalstock=[]
        onlyfiles = [ f for f in listdir(self.stockdata) if isfile(join(self.stockdata,f)) ]
        for f in onlyfiles:
            s=f.split('.')
            name=s[0][2:8]
            totalstock.append(name)
            
        data = {'codes': totalstock}
        frame = DataFrame(data)
        
        self.pool['all'].insert_many(json.loads(frame.to_json(orient='records')))
        print (frame)
            
        

if __name__ == '__main__':
    l=LoadDataCVS('127.0.0.1',27017)
    l.Conn()
    #l.storagedaily()
    #l.storageindex()
    # l.storagepool()
    # l.storageStockName()
    #l.insert_zipline_treasure_format()
    #l.Close()
    
    #l.storageStockName()
    #print l.getstocklist('all')

