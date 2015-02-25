# -*- coding: utf-8 -*-
"""
Module IBClient, Created on Wed Dec 17 13:04:49 2014

@author: Huapu (Peter) Pan
"""
import datetime, time, pytz
import numpy as np
#import logging
import BasicPyLib.simpleLogger as simpleLogger

import IBCpp  # IBCpp.pyd is the Python wrapper to IB C++ API
from IBridgePy.IBridgePyBasicLib.quantopian import Security, ContextClass, \
PositionClass, HistClass, create_contract, MarketOrder,create_order, \
OrderClass, same_security, DataClass, symbol, symbols
from IBridgePy.IBridgePyBasicLib.IBAccountManager import IBAccountManager
from IBridgePy.IBridgePyBasicLib.MarketManagerBase import MarketManager
from BasicPyLib.FiniteState import FiniteStateClass
    
class TickTrader(IBAccountManager):
    """
    BarTraders are IBAccountManager too, so BarTraders inherits from IBAccountManager.
    Besides managing the account, BarTraders also make trade decisions for every
    unit time bar, such as 1 minute
    """
    def setup(self, PROGRAM_DEBUG = False, TRADE_DEBUG = True, port = 7496, clientId = 1,
              accountCode = 'ALL', maxSaveTime = 1800, minTick = 0.01, 
              logLevel = simpleLogger.INFO):
        '''
        initialize BarTrader. First initialize the parent class IBAccountManager,
        then define the data structure for saving security data. 
        '''
        # call parent class's setup
        super(TickTrader, self).setup(PROGRAM_DEBUG = PROGRAM_DEBUG, 
            TRADE_DEBUG = TRADE_DEBUG, accountCode = accountCode, 
            minTick = minTick, maxSaveTime = maxSaveTime, port = port, 
            clientId = clientId, logLevel = logLevel) 
            
        # traderState
        class TraderStateClass(FiniteStateClass):
            """ define possible states of traderState """
            def __init__(self):
                self.INIT = 'INIT'; self.TRADE = 'TRADE'
        self.traderState = TraderStateClass()
        self.traderState.set_state(self.traderState.INIT)
        
        self.reqPositions()
        self.context.portfolio.start_date=datetime.datetime.now()
    
    def API_initialize(self):
        # call Quantopian-like user API function
        initialize(self.context)
        # data is used to save the current security price info        
        self.setup_data()
        
    ############# this function is running in an infinite loop
    def runAlgorithm(self):
        print 'runAlgorithm'
        time.sleep(0.1) # sleep to avoid exceeding IB's max data rate
        self.reqCurrentTime()
        # initialize
        if self.traderState.is_state(self.traderState.INIT):
            if self.accountManagerState.is_state(self.accountManagerState.INIT):
                self.log.info(__name__ + ": " + "entering INIT stage")
                self.req_hist_price(endtime=datetime.datetime.now(), 
                                    goback='60 D', barSize='1 day')
                self.re_send = 0
                self.req_real_time_price() # request market data
                self.set_timer()
                self.accountManagerState.set_state(
                    self.accountManagerState.WAIT_FOR_INIT_CALLBACK)
                
            if self.accountManagerState.is_state(
                    self.accountManagerState.WAIT_FOR_INIT_CALLBACK): 
                self.check_timer(self.accountManagerState.WAIT_FOR_INIT_CALLBACK)
                if self.req_hist_price_check_end() and self.nextOrderId_Status =='Done': 
                    # update historical data for each security
                    for security in self.returned_hist:
                        self.data[security].hist_daily = \
                            self.returned_hist[security].hist
                    self.traderState.set_state(self.traderState.TRADE)
                    self.accountManagerState.set_state(self.accountManagerState.SLEEP)
                    self.log.info(__name__ + ": " + "completing init stage")

        # every tick
        if self.traderState.is_state(self.traderState.TRADE):
                # Run handle_data
                handle_data(self.context, self.data)
                
if __name__ == "__main__":
    import pandas as pd
    settings = pd.read_csv('settings.csv')
    
    trader = TickTrader()
    trader.setup(PROGRAM_DEBUG = True, accountCode = settings['AccountCode'][0], 
                 logLevel = simpleLogger.NOTSET)
    ########## API
    order_with_SL_TP = trader.order_with_SL_TP
    log = trader.log
    history=trader.history_quantopian
    ##########
    
    ###### read in the algorithm script

    print "Now running algorithm: ", settings['Algorithm'][0]
    with open('algos/' + settings['Algorithm'][0] + '.py') as f:
        script = f.read()
    #print script
    exec(script)
    ######
        
    trader.API_initialize()
#    trader.connect("", 7496, 1)
#    trader.disconnect()
    
    c = MarketManager(PROGRAM_DEBUG = True, trader = trader)
    c.run_according_to_market(market_start_time = '00:00:01',
                              market_close_time = '23:59:59')
    
    print("Finished!")