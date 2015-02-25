# -*- coding: utf-8 -*-
"""
Created on Wed Mar 26 18:44:04 2014

@author: huapu
"""

import IBCpp  # You need to link/copy IBCpp.so to the same directory 
#import sys
#import os
import pandas as pd
import datetime
import pytz
import time
from dateutil.tz import tzlocal
#import numpy as np
import matplotlib.pylab as plt

class GetHistData(IBCpp.IBClient):
    def setup(self):
        self.time_last_request_hist = None
        self._empty_df = pd.DataFrame(columns = 
            ['symbol', 'open','high','low','close', 
             'volume', 'barCount', 'WAP'])
        self.hist = self._empty_df 
        self.req_hist_Id = 0
        self.request_hist_data_status = None
        self.currentHistSymbol = ""
        self.stime=None
        self.state='first'
        """ determine US Eastern time zone depending on EST or EDT """
        if datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EDT':
            #self.USeasternTimeZone = pytz.timezone('Etc/GMT+4')
            self.USeasternTimeZone = pytz.timezone('EDT')
        elif datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EST':
            #self.USeasternTimeZone = pytz.timezone('Etc/GMT+5')   
            self.USeasternTimeZone = pytz.timezone('EST')   
        else:
            self.USeasternTimeZone = None      
        
    def error(self, errorId, errorCode, errorString):
        print 'errorId = ' + str(errorId), 'errorCode = ' + str(errorCode)
        print 'error message: ' + errorString
        
    def request_hist_data(self, contract, endDateTime, durationStr, barSizeSetting):   
#        if (self.request_hist_data_status is not None and \
#        (datetime.datetime.now()-self.time_last_request_hist).total_seconds()<=16):
#            print "sleep for 16 seconds to avoid pace violation"
#            time.sleep(16)
        self.hist = self._empty_df
        self.req_hist_Id = self.req_hist_Id + 1
        self.currentHistSymbol = contract.symbol
        print "request historical data for %s" % (contract.symbol)
        self.reqHistoricalData(self.req_hist_Id, contract, endDateTime , 
                               durationStr, barSizeSetting, 'BID', 1, 1)
        # Record the latest time when the hist data was requested
        self.time_last_request_hist=datetime.datetime.now() 
        self.request_hist_data_status='Submitted'
        #while (self.request_hist_data_status != 'Done'):
        #    self.processMessages()
        
    def historicalData(self, reqId, date, price_open, price_high, price_low, 
                       price_close, volume, barCount, WAP, hasGaps):
        if reqId==self.req_hist_Id:           
            if 'finished' in str(date):
                self.request_hist_data_status='Done'
            else: 
                if '  ' in date: # Two datetime structues may come back
                    date=datetime.datetime.strptime(date, '%Y%m%d  %H:%M:%S')                        
                else:
                    date=datetime.datetime.strptime(date, '%Y%m%d') 
                if date in self.hist.index: # Write data to self.hist
                    self.hist['symbol'][date] = self.currentHistSymbol
                    self.hist['open'][date]=price_open
                    self.hist['high'][date]=price_high
                    self.hist['low'][date]=price_low
                    self.hist['close'][date]=price_close
                    self.hist['volume'][date] = volume
                    self.hist['barCount'][date] = barCount
                    self.hist['WAP'][date] = WAP
                else:
                    newRow = pd.DataFrame({'open':price_open,'high':price_high,
                                           'low':price_low,'close':price_close, 
                                           'volume': volume, 'barCount': barCount, 
                                           'WAP': WAP,
                                           'symbol': self.currentHistSymbol},
                                          index = [date])
                    self.hist=self.hist.append(newRow)
        else:
            print 'reqId is not the same as req_hist_Id.' + \
                'Please request historical data through request_hist_data() function'

#            self.state = "datareqed" # change the state so that you won't request the same data again. 

    def currentTime(self, tm):
        """
        IB C++ API call back function. Return system time in datetime instance
        constructed from Unix timestamp using the USeasternTimeZone from MarketManager
        """
        self.stime = datetime.datetime.fromtimestamp(float(str(tm)), 
                                                    tz = self.USeasternTimeZone)

    def runStrategy(self):
        if self.state=='first':
            #print self.stime
            if self.stime!=None and self.stime.second==4:
                #print self.stime
                #print self.stime.tzname()
                req = datetime.datetime.strftime(self.stime,"%Y%m%d %H:%M:%S %Z") #datatime -> string                print dt_stime                
                #print req
                s = 'EUR.USD'
                contract = IBCpp.Contract()
                contract.symbol = s.split('.')[0]
                contract.currency = s.split('.')[-1]        
                contract.secType = 'CASH'
                contract.exchange = 'IDEALPRO'
                contract.primaryExchange = 'IDEALPRO'
                #c.request_hist_data(contract, '20150219  09:31:00 EST', '60 S', '30 secs')
                c.request_hist_data(contract, req, '60 S', '30 secs')
                self.state='second'
        if self.state=='second':
            if self.request_hist_data_status=='Done':
                print self.hist
                print self.hist.iloc[0]['open']
                exit()
            
            
if __name__ == '__main__' :
    # connect to IB
    port = 7496; clientID = 1
    c = GetHistData()
    c.setup()
    c.connect("", port, clientID)

    # request server time    
    c.reqCurrentTime()
    
    while(1):
        time.sleep(1)
        c.processMessages()
        c.runStrategy()
        c.reqCurrentTime()
   