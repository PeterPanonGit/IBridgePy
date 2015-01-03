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
        
    def error(self, errorId, errorCode, errorString):
        print 'errorId = ' + str(errorId), 'errorCode = ' + str(errorCode)
        print 'error message: ' + errorString
        
    def request_hist_data(self, contract, endDateTime, durationStr, barSizeSetting):   
        if (self.request_hist_data_status is not None and \
        (datetime.datetime.now()-self.time_last_request_hist).total_seconds()<=16):
            print "sleep for 16 seconds to avoid pace violation"
            time.sleep(16)
        self.hist = self._empty_df
        self.req_hist_Id = self.req_hist_Id + 1
        self.currentHistSymbol = contract.symbol
        print "request historical data for %s" % (contract.symbol)
        self.reqHistoricalData(self.req_hist_Id, contract, endDateTime , 
                               durationStr, barSizeSetting, 'TRADES', 1, 1)
        # Record the latest time when the hist data was requested
        self.time_last_request_hist=datetime.datetime.now() 
        self.request_hist_data_status='Submitted'
        
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
            
if __name__ == '__main__' :
    # connect to IB
    port = 7496; clientID = 1
    c = GetHistData(); c.setup(); c.connect("", port, clientID)
    # create contract and request historical data
    contract = IBCpp.Contract()
    contract.symbol = 'IBM'; contract.secType = 'STK'
    contract.exchange = 'SMART'; contract.primaryExchange = 'NYSE'
    c.request_hist_data(contract, '20141212  10:00:00 EST', '1 D', '30 secs')
    while(c.request_hist_data_status != 'Done'):
        c.processMessages()
    # disconnect
    c.disconnect()
    print c.hist