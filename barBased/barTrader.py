
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
    
class BarTrader(IBAccountManager):
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
        super(BarTrader, self).setup(PROGRAM_DEBUG = PROGRAM_DEBUG, 
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
        time.sleep(0.1) # sleep to avoid exceeding IB's max data rate
        self.reqCurrentTime()
        # initialize
        if self.traderState.is_state(self.traderState.INIT):
            if self.accountManagerState.is_state(self.accountManagerState.INIT):
                self.log.info(__name__ + ": " + "entering INIT stage")
                print 'entering INIT stage'

                self.req_real_time_price()                     # request market data
                self.reqAccountUpdates(True,self.accountCode)  # Request to update account info

                # Request multiple hist price
                self.re_send = 0
                self.returned_hist= {}   
                for security in self.data:     
                    for period in self.context.hist_frame:
                        self.req_hist_price(security, endtime=datetime.datetime.now(), barSize=period)
                self.set_timer()
                
                # change machine state
                self.accountManagerState.set_state(
                    self.accountManagerState.WAIT_FOR_INIT_CALLBACK)
            if self.accountManagerState.is_state(
                    self.accountManagerState.WAIT_FOR_INIT_CALLBACK): 
                self.check_timer(self.accountManagerState.WAIT_FOR_INIT_CALLBACK,10)
                if self.req_hist_price_check_end(): 
                    for req_id in self.returned_hist:
                        for security in self.data:
                            if same_security(security, self.returned_hist[req_id].security):
                                self.data[security].hist[self.returned_hist[req_id].period]=self.returned_hist[req_id].hist
                    self.traderState.set_state(self.traderState.TRADE)
                    self.accountManagerState.set_state(self.accountManagerState.SLEEP)
                    self.log.info(__name__ + ": " + "completing init stage")
                    print 'INIT stage completed'

        # 
        if self.traderState.is_state(self.traderState.TRADE):
            # at the beginning of every minute, update hist and accountINFO
            if self.stime.second==0 and self.stime_previous.second!=0:
                #print 'beginning of minute'
                self.re_send = 0
                self.returned_hist= {}   
                for security in self.data:     
                    for period in self.context.hist_frame:
                        if period=='1 min':
                            goback='120 S'
                        elif period=='1 day':
                            goback='2 D'
                        elif period=='1 hour':
                            goback='7200 S'
                        elif period=='4 hours':
                            goback='1 D'
                        elif period=='10 mins':
                            goback='1200 S'
                        self.req_hist_price(security, endtime=self.stime, goback=goback, barSize=period)
                self.set_timer()
                self.accountManagerState.set_state(self.accountManagerState.WAIT_FOR_BAR_PRICE_CALLBACK)
            if self.accountManagerState.is_state(self.accountManagerState.WAIT_FOR_BAR_PRICE_CALLBACK): 
                if self.req_hist_price_check_end(): 
                    # After receive the new hist, combine them with the old hist
                    for req_id in self.returned_hist:
                        #print self.returned_hist[req_id].hist                      
                        for security in self.data:
                            if same_security(security, self.returned_hist[req_id].security):
                                temp=self.data[security].hist[self.returned_hist[req_id].period]
                                empty=pd.DataFrame(columns=['open','high','low','close','volume'])
                                for index in temp.index:
                                    if index not in self.returned_hist[req_id].hist.index:
                                        empty=empty.append(temp.loc[index])
                                self.data[security].hist[self.returned_hist[req_id].period]=empty.append(self.returned_hist[req_id].hist)        
                                #print empty
                                #print self.returned_hist[req_id].hist
                                #print self.data[security].hist[self.returned_hist[req_id].period]
                                        #self.data[security].hist[self.returned_hist[req_id].period]= \
                                        #temp.append(self.returned_hist[req_id].hist.loc[index])
                    for security in self.data:
                        for period in self.context.hist_frame:
                            if len(self.data[security].hist[period])>300:
                                self.data[security].hist[period]=self.data[security].hist[period][-300:]
                            #print self.data[security].hist[period]
                    self.accountManagerState.set_state(self.accountManagerState.EVERY_BAR_RUN)
                    

                    # Run handle_data regularly
                    handle_data(self.context, self.data)
                    #print self.stime

        self.stime_previous=self.stime        
                
if __name__ == "__main__":
    import pandas as pd
    settings = pd.read_csv('settings.csv')
    
    trader = BarTrader()
    trader.setup(PROGRAM_DEBUG = False, accountCode = settings['AccountCode'][0], 
                 logLevel = simpleLogger.ERROR)
    ########## API
    order_with_SL_TP = trader.order_with_SL_TP
    log = trader.log
    history=trader.history_quantopian
    get_datetime=trader.get_datetime_quantopian
    ##########
    
    ###### read in the algorithm script

    print "Now running algorithm: ", settings['Algorithm'][0]
    with open('algos/' + settings['Algorithm'][0] + '.py') as f:
        script = f.read()
#    print script
    exec(script)
    ######
        
    trader.API_initialize()
#    trader.connect("", 7496, 1)
#    trader.disconnect()
    
    c = MarketManager(PROGRAM_DEBUG = False, MARKET_DEBUG = False, trader = trader)
    c.run_according_to_market(market_start_time = '00:00:00',
                              market_close_time = '23:59:59')
    
    print("Finished!")