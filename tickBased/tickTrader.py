# -*- coding: utf-8 -*-
"""
Module IBClient, Created on Wed Dec 17 13:04:49 2014

@author: Huapu (Peter) Pan
"""
import datetime, time, pytz
import numpy as np
import logging

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
              USeasternTimeZone = None, accountCode = 'ALL', minTick = 0.01):
        '''
        initialize BarTrader. First initialize the parent class IBAccountManager,
        then define the data structure for saving security data. 
        '''
        # call parent class's setup
        super(TickTrader, self).setup(PROGRAM_DEBUG = PROGRAM_DEBUG, 
            TRADE_DEBUG = TRADE_DEBUG, USeasternTimeZone = USeasternTimeZone, 
            accountCode = accountCode, minTick = minTick, port = port, clientId = clientId) 
            
        # max timeframe to be saved in price_size_last_matrix for TickTrader
        self.maxSaveTime = 3600 # seconds
        
        # traderState
        class TraderStateClass(FiniteStateClass):
            """ define possible states of traderState """
            def __init__(self):
                self.INIT = 'INIT'; self.TRADE = 'TRADE'
        self.traderState = TraderStateClass()
        self.traderState.set_state(self.traderState.INIT)
        
        self.reqCurrentTime() # update stime
        self.reqPositions()
        self.context.portfolio.start_date=datetime.datetime.now()
    
    def API_initialize(self):
        # call Quantopian-like user API function
        initialize(self.context)
        # data is used to save the current security price info        
        self.data = {}; 
        if len(self.context.security) >= 2:
            for ct in self.context.security:
                self.data[ct] = DataClass()
                # 0 = trade timestamp; 1 = price_last; 2 = size_last; 3 = record_timestamp
                self.data[ct].RT_volume = np.zeros(shape = (0,4))
        else:
            self.data[self.context.security] = DataClass()
            self.data[self.context.security].RT_volume = np.zeros(shape = (0,4))        
        
    def tickString(self, tickerId, field, value):
        """
        IB C++ API call back function. The value variable contains the last 
        trade price and volume information. User show define in this function
        how the last trade price and volume should be saved
        """
        sec = self.context.security[tickerId]
        currentTime = datetime.datetime.now(tz = self.USeasternTimeZone)
        valueSplit = value.split(';')
        if len(valueSplit) > 1 and float(valueSplit[1]) > 0:
            timePy = float(valueSplit[2])/1000
            priceLast = float(valueSplit[0]); sizeLast = float(valueSplit[1])
            currentTimeStamp = time.mktime(datetime.datetime.now().timetuple())
            self.log.debug(__name__ + ', ' + str(sec.symbol) + ', ' + str(priceLast)
            + str(sizeLast) + ', ' + str(timePy) + ', ' + str(currentTime))
            # update price
            newRow = [float(valueSplit[2])/1000, priceLast, sizeLast, currentTimeStamp]
            priceSizeLastSymbol = self.data[sec].RT_volume
            priceSizeLastSymbol = np.vstack([priceSizeLastSymbol, newRow])
            # erase data points that go over the limit
            if (timePy - priceSizeLastSymbol[0, 0]) > self.maxSaveTime:
                priceSizeLastSymbol = priceSizeLastSymbol[1:,:]
            self.data[sec].RT_volume = priceSizeLastSymbol
            
    def order_with_SL_TP(self, sec, amount, orderId = None, 
                         stopLossPrice = None, takeProfitPrice = None):
        '''
        This function make orders. When amount > 0 it is BUY and when amount < 0 it is SELL
        '''
        # fill order info
        if amount > 0:
            orderAction = 'BUY'
            orderReverseAction = 'SELL'
            amount = int(amount)
        elif amount < 0:
            orderAction = 'SELL'
            orderReverseAction = 'BUY'
            amount = int(np.abs(amount))
        else:
            self.log.warning("order amount is 0!")
            return
            
        if (stopLossPrice is None):
            self.log.warning("can not place an order without stop loss!")
            return
        # fill contract info
        contract = create_contract(sec)
        ### place order
        # market order
        marketOrder = IBCpp.Order()
        marketOrder.action = orderAction
        marketOrder.totalQuantity = amount
        marketOrder.orderType = 'MKT'
        marketOrder.transmit = False
        marketOrder.account = self.accountCode
        parentOrderId = self.nextOrderId
        self.placeOrder(parentOrderId, contract, marketOrder)
        if not (parentOrderId in self.context.portfolio.openOrderBook):
            self.context.portfolio.openOrderBook[parentOrderId] = \
                OrderClass(orderId = parentOrderId, parentOrderId = None,
                    created=datetime.datetime.now(),
                    stop = None,
                    limit = None,
                    amount = marketOrder.totalQuantity,
                    sid = Security(contract.symbol+'.'+contract.currency),
                    status = 'PreSubmitted',
                    contract = contract,
                    order = marketOrder,
                    orderstate = None)
        self.nextOrderId += 1
        # stop sell order: stop loss
        childOrder = IBCpp.Order()
        childOrder.action = orderReverseAction
        childOrder.totalQuantity = amount
        childOrder.orderType = 'STP'
        childOrder.auxPrice = self.roundToMinTick(stopLossPrice)
        childOrder.parentId = parentOrderId
        if (takeProfitPrice is None):
            childOrder.transmit = True # if not limit order transmit STP order
        else:
            childOrder.transmit = False
        childOrder.account = self.accountCode
        childOrderId = self.nextOrderId
        childOrder.ocaGroup = str(parentOrderId)
        self.placeOrder(childOrderId, contract, childOrder)
        if not (childOrderId in self.context.portfolio.openOrderBook):
            self.context.portfolio.openOrderBook[childOrderId] = \
                OrderClass(orderId = childOrderId, parentOrderId = parentOrderId,
                    created=datetime.datetime.now(),
                    stop = stopLossPrice,
                    limit = None,
                    amount = childOrder.totalQuantity,
                    sid = Security(contract.symbol+'.'+contract.currency),
                    status = 'PreSubmitted',
                    contract = contract,
                    order = childOrder,
                    orderstate = None)
        self.nextOrderId += 1
        # limit sell order: take profit
        # Limit order: an order to buy or sell at a specified price or better.
        if (takeProfitPrice is not None):
            childOrder = IBCpp.Order()
            childOrder.action = orderReverseAction
            childOrder.totalQuantity = amount
            childOrder.orderType = 'LMT'
            childOrder.lmtPrice = self.roundToMinTick(takeProfitPrice)
            childOrder.parentId = parentOrderId
            childOrder.transmit = True
            childOrder.account = self.accountCode
            childOrderId = self.nextOrderId
            childOrder.ocaGroup = str(parentOrderId)
            self.placeOrder(childOrderId, contract, childOrder)
            if not (childOrderId in self.context.portfolio.openOrderBook):
                self.context.portfolio.openOrderBook[childOrder] = \
                    OrderClass(orderId = childOrderId, parentOrderId = parentOrderId,
                        created=datetime.datetime.now(),
                        stop = None,
                        limit = takeProfitPrice,
                        amount = childOrder.totalQuantity,
                        sid = Security(contract.symbol+'.'+contract.currency),
                        status = 'PreSubmitted',
                        contract = contract,
                        order = childOrder,
                        orderstate = None)   
            self.nextOrderId += 1
        # print order placement time    
        self.log.info(__name__ + ": " + 'order placed at: ' + str(datetime.datetime.now(self.USeasternTimeZone)))
    
        return self.nextOrderId
        
    ############# this function is running in an infinite loop
    def runAlgorithm(self):
        time.sleep(0.1) # sleep to avoid exceeding IB's max data rate
        self.reqCurrentTime()
        # initialize
        if self.traderState.is_state(self.traderState.INIT):
            if self.accountManagerState.is_state(self.accountManagerState.INIT):
                self.req_hist_price(endtime=datetime.datetime.now(), 
                                    goback='3 D', barSize='1 day')
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
                    
        # main: every bar
        if self.traderState.is_state(self.traderState.TRADE):
                # Run handle_data
                handle_data(self.context, self.data)
                
if __name__ == "__main__":
    import pandas as pd
    settings = pd.read_csv('settings.csv')
    
    trader = TickTrader()
    trader.setup(PROGRAM_DEBUG = True, accountCode = settings['AccountCode'][0])
    ########## API
    order_with_SL_TP = trader.order_with_SL_TP
    log = trader.log
    ##########
    
    ###### read in the algorithm script

    print "Now running algorithm: ", settings['Algorithm'][0]
    with open('algos/' + settings['Algorithm'][0] + '.py') as f:
        script = f.read()
#    print script
    exec(script)
    ######
        
    trader.API_initialize()
    
    c = MarketManager(PROGRAM_DEBUG = True, trader = trader)
    c.run_according_to_market(market_start_time = '9:29:55', 
                              market_close_time = '16:00:00')
    
    print("Finished!")