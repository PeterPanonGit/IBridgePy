# -*- coding: utf-8 -*-
"""
Created on Wed Mar 26 18:44:04 2014

@author: huapu
"""

import IBpy  # You need to link/copy IBpy.so to the same directory 
#import sys
#import os
import pandas as pd
import datetime
import pytz
import time
from dateutil.tz import tzlocal
#import numpy as np
import matplotlib.pylab as plt

class realTime_Multiple_Stocks(IBpy.IBClient) :  #  define a new client class. All client classes are recommended to derive from IBClient unless you have special need.  
    def setup(self):
        self.state = "initial"
        self.contract_list = pd.read_csv('test_contract_list.csv', index_col = 0)
        self.nextValidId_number = 0
        self.hist_open = pd.DataFrame()
        self.hist_high = pd.DataFrame()
        self.hist_low = pd.DataFrame()
        self.hist_close = pd.DataFrame()
        self.hist_volume = pd.DataFrame()        
        # timezone info; only useful in getHistoricalData
        if datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EDT':
            self.USeasternTimeZone = pytz.timezone('Etc/GMT+4')
        else:
            self.USeasternTimeZone = pytz.timezone('Etc/GMT+5')        
        
    def error(self, errorId, errorCode, errorString):
        if errorId > 0:
            symbol = self.contract_list['symbol'][errorId]
        else:
            symbol = ''
        print 'errorId = ' + str(errorId), 'symbol = ' + symbol, 'errorCode = ' + str(errorCode)
        print 'error message: ' + errorString
                   
    def historicalData(self, reqId, date, price_open, high, low, price_close, volume, barCount, WAP, hasGaps):
        symbol = self.contract_list['symbol'][reqId]
        if 'finished' in str(date):
            return
        else:
            date = str(date)
        ymd, hms = date.split('  ')
        time_str = ymd[:4] + '-' + ymd[4:6] + '-' + ymd[6:8] + ' ' + hms
        time_py = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
        time_py = time_py.replace(tzinfo = tzlocal())
#        time_py = time_py.astimezone(pytz.timezone('Etc/GMT+5'))
        time_py = time_py.astimezone(self.USeasternTimeZone)
#        print time_str
        if not (time_py in self.hist_close.index):
            newRow = pd.DataFrame({k + ' open': pd.Series() for k in self.contract_list['symbol']}, index = [time_py])
            newRow[symbol + ' open'] = price_open
            self.hist_open = self.hist_open.append(newRow)
            newRow = pd.DataFrame({k + ' high': pd.Series() for k in self.contract_list['symbol']}, index = [time_py])
            newRow[symbol + ' high'] = high
            self.hist_high = self.hist_high.append(newRow)
            newRow = pd.DataFrame({k + ' low': pd.Series() for k in self.contract_list['symbol']}, index = [time_py])
            newRow[symbol + ' low'] = low
            self.hist_low = self.hist_low.append(newRow)
            newRow = pd.DataFrame({k + ' close': pd.Series() for k in self.contract_list['symbol']}, index = [time_py])
            newRow[symbol + ' close'] = price_close
            self.hist_close = self.hist_close.append(newRow)    
            newRow = pd.DataFrame({k + ' volume': pd.Series() for k in self.contract_list['symbol']}, index = [time_py])
            newRow[symbol + ' volume'] = volume
            self.hist_volume = self.hist_volume.append(newRow)
        else:
            self.hist_open[symbol + ' open'][time_py] = price_open
            self.hist_high[symbol + ' high'][time_py] = high
            self.hist_low[symbol + ' low'][time_py] = low
            self.hist_close[symbol + ' close'][time_py] = price_close
    
    def plot_price_volume(self, symbol, startTime, endTime):
        ax = plt.subplot(2, 1, 1)
        self.hist_close[symbol + ' close'][startTime:endTime].plot(ax = ax)
        self.hist_open[symbol + ' open'][startTime:endTime].plot(ax = ax)
        self.hist_high[symbol + ' high'][startTime:endTime].plot(ax = ax)
        self.hist_low[symbol + ' low'][startTime:endTime].plot(ax = ax)
        ax.legend().set_visible(False)
        ax.axes.get_xaxis().set_visible(False)
        ax = plt.subplot(2, 1, 2)
        self.hist_volume[symbol + ' volume'][startTime:endTime].plot(ax = ax)
        plt.show()
            
    def runStrategy(self) :
        '''
        This should be your trading strategy's main entry. It will be called at the beginning of processMessages()
        '''
        pass

#            self.state = "datareqed" # change the state so that you won't request the same data again. 
            
if __name__ == '__main__' :
    port = 7496
#    port = 4001
    clientID = 1

    c = realTime_Multiple_Stocks()  # create a client object
    c.setup()      # additional setup. It's optional.
    c.connect("", port, clientID) # you need to connect to the server before you do anything. 
    dataDate = '2014-04-14'
    startTime = datetime.datetime.strptime(dataDate + ' 9:30:00', '%Y-%m-%d %H:%M:%S')
    startTime = startTime.replace(tzinfo = c.USeasternTimeZone)
    endTime = datetime.datetime.strptime(dataDate + ' 15:59:30', '%Y-%m-%d %H:%M:%S')
    endTime = endTime.replace(tzinfo = c.USeasternTimeZone)    
    for ii, con in c.contract_list[:1].iterrows():
        c.setup()
        contract = IBpy.Contract()
        symbol = con['symbol']
        contract.symbol = con['symbol']
        contract.secType = con['secType']
        contract.exchange = con['exchange']
        contract.primaryExchange = con['primaryExchange']
        c.reqHistoricalData(ii, contract, ''.join(dataDate.split('-')) + ' 19:05:00 EST', 
                               '1 D', '30 secs', 'TRADES', 1, 1)
        time.sleep(1)        
        while(1):
            c.processMessages()       # put this function into infinit loop. A better way is to put it into a new thread.             
            if len(c.hist_close) > 0 and (c.hist_close.index[-1] == endTime):
                c.plot_price_volume(symbol, startTime, endTime)
                c.cancelHistoricalData(ii)     
                break            