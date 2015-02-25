# -*- coding: utf-8 -*-

import datetime, time
import pandas as pd
import numpy as np
import logging
import os
import pytz

from IBridgePy.IBridgePyBasicLib.quantopian import Security, ContextClass, PositionClass, \
HistClass, create_contract, MarketOrder, create_order, OrderClass, same_security, \
DataClass
import IBCpp
from BasicPyLib.FiniteState import FiniteStateClass
import BasicPyLib.simpleLogger as simpleLogger

# https://www.interactivebrokers.com/en/software/api/apiguide/tables/tick_types.htm
MSG_TABLE = {0: 'bid size', 1: 'bid price', 2: 'ask price', 3: 'ask size', 
             4: 'last price', 5: 'last size', 6: 'daily high', 7: 'daily low', 
             8: 'daily volume', 9: 'close', 14: 'open'}

class IBAccountManager(IBCpp.IBClient):
    """
    IBAccountManager manages the account, order, and historical data information
    from IB. These information are needed by all kinds of traders.
    stime: system time obtained from IB
    maxSaveTime: max timeframe to be saved in price_size_last_matrix for TickTrader
    """
    def setup(self, PROGRAM_DEBUG = False, TRADE_DEBUG = True,
              accountCode = 'ALL', minTick = 0.01, 
              maxSaveTime = 0, port = 7496, clientId = 1, logLevel = simpleLogger.INFO):
        """
        initialize the IBAccountManager. We don't do __init__ here because we don't
        want to overwrite parent class IBCpp.IBClient's __init__ function
        """
        # timezone info passed from MarketManager
        self.USeasternTimeZone = None
        
        # traderState
        class AccountManagerStateClass(FiniteStateClass):
            """ define possible states of traderState """
            def __init__(self):
                self.INIT = 'INIT'
                self.WAIT_FOR_INIT_CALLBACK = 'WAIT_FOR_INIT_CALLBACK'
                self.REQ_BAR_PRICE = 'REQ_BAR_PRICE'
                self.REQ_DAILY_PRICE = 'REQ_DAILY_PRICE'
                self.WAIT_FOR_DAILY_PRICE_CALLBACK = 'WAIT_FOR_DAILY_PRICE_CALLBACK'
                self.WAIT_FOR_BAR_PRICE_CALLBACK = 'WAIT_FOR_BAR_PRICE_CALLBACK'
                self.UPDATE_PORTFOLIO = 'UPDATE_PORTFOLIO'
                self.WAIT_FOR_UPDATE_PORTFOLIO_CALLBACK = 'WAIT_FOR_UPDATE_PORTFOLIO_CALLBACK'
                self.EVERY_BAR_RUN = 'EVERY_BAR_RUN'
                self.SLEEP = 'SLEEP'
        self.accountManagerState = AccountManagerStateClass()
        self.accountManagerState.set_state(self.accountManagerState.INIT)
        
        self.returned_hist= {}
        self.data = {}
        self.accountDownloadEndstatus='na'
        self.stime_previous = None
        self.stime = None
        self.context = ContextClass()
        self.context.USeasternTimeZone = self.USeasternTimeZone
        self.last_message='na'
        self.minTick = minTick
        self.maxSaveTime = maxSaveTime # maxSaveTime is the duration for saving flow data. Unit: seconds
        
        # accountCode
        self.accountCode = accountCode
        
        # port and clientId
        self.port = port; self.clientId = clientId
            
        # Id tracker and status flags
        self.nextOrderId_Status = 'none'
        self.nextOrderId = 0
        self.nextReqMktDataId = 0
        self.nextHistDataId = 0
        
        # DEBUG levels
        self.PROGRAM_DEBUG = PROGRAM_DEBUG
        self.TRADE_DEBUG = TRADE_DEBUG
        
        # trader log
#        logger = logging.getLogger('TraderLog')
#        logger.setLevel(logging.NOTSET)
#        # create a file handler
        self.todayDateStr = time.strftime("%Y-%m-%d")
#        file_handler = logging.FileHandler('Log/TraderLog_' + self.todayDateStr + '.txt', mode = 'w')
#        file_handler.setLevel(logging.NOTSET)
#        console_handler = logging.StreamHandler()
#        console_handler.setLevel(logging.NOTSET)
#        # create a logging format
#        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#        file_handler.setFormatter(formatter)
#        console_handler.setFormatter(formatter)
#        # add the handlers to the logger
#        logger.addHandler(file_handler)
#        logger.addHandler(console_handler)
        self.log = simpleLogger.SimpleLoggerClass(filename = 
        'TraderLog_' + self.todayDateStr + '.txt', logLevel = logLevel)
        self.log.info(__name__ + ": " + "accountCode: " + str(self.accountCode))
        
        # setup IB's log file and message level
        self.logFileName = "IB_system_log.txt"
        self.logOn()
        self.echo = True
        self.addMessageLevel(IBCpp.MsgLevel.SYSERR)
        self.addMessageLevel(IBCpp.MsgLevel.IBINFO)
        self.log.info(__name__ + ": " + 
        "IB message level: " + "{0:b}".format(self.getMessageLevel()))
            
    def setup_data(self):
        """
        setup self.data after the initialize() API is run
        """
        self.data={}; 
        try:        
            if len(self.context.security)>=2:
                for ct in self.context.security:
                    self.data[ct] = DataClass()
        except:
            self.data[self.context.security] = DataClass(hist_frame=self.context.hist_frame)
            
    def error(self, errorId, errorCode, errorString):
        """
        only print real error messages, which is errorId < 2000 in IB's error
        message system, or program is in debug mode
        """
        if errorCode < 2000:
            self.log.error(__name__ + ": " + 'errorId = ' + str(errorId) + 
            ', errorCode = ' + str(errorCode) + ', error message: ' + errorString)
            
    def currentTime(self, tm):
        """
        IB C++ API call back function. Return system time in datetime instance
        constructed from Unix timestamp using the USeasternTimeZone from MarketManager
        """
        self.stime = datetime.datetime.fromtimestamp(float(str(tm)), 
                                                    tz = self.USeasternTimeZone)
#        if (self.PROGRAM_DEBUG):
#            print "current IB system time: ", self.stime
        
    def roundToMinTick(self, price):
        """
        for US interactive Brokers, the minimum price change in US stocks is
        $0.01. So if the user made calculations on any price, the calculated
        price must be round using this function to the minTick, e.g., $0.01
        """
        self.log.debug(__name__ + ": " + 'roundToMinTick price: ' + str(price) +
        str(type(price)) + str(type(self.minTick)))
        return int(price / self.minTick) * self.minTick
    ######################   SUPPORT ############################33

#    timer_start=datetime.datetime.now()
#    re_send=0
    def set_timer(self):
        """
        set self.timer_start to current time so as to start the timer
        """
        self.timer_start = datetime.datetime.now(tz = self.USeasternTimeZone)
        self.log.debug(__name__ + ": " + "set timer" + str(self.timer_start))
        
    def check_timer(self, step, limit = 1):
        """
        check_timer will check if time limit exceeded for certain
        steps, including: updated positions, get nextValidId, etc
        """
        timer_now = datetime.datetime.now(tz = self.USeasternTimeZone)
        change = (timer_now-self.timer_start).total_seconds()
        if change > limit: # if time limit exceeded
            if step == self.accountManagerState.WAIT_FOR_INIT_CALLBACK:
                if self.nextOrderId_Status !='Done':
                    self.log.error(__name__ + ": " + 'Time Limit Exceeded when \
                    requesting nextValidId' + str(step,datetime.datetime.now()) + \
                    '\n' + 'self.nextValidId_status = ' + str(self.nextValidId_status))
                    exit()
                elif self.req_real_time_price_check_end() != 'Done':
                    self.log.error(__name__ + ": " + 'ERROR in receiving real time quotes')                    
                    for security in self.data:
                        security.print_obj()
                        #for ct in [self.data[security].bid_price,self.data[security].ask_price]:                              
                        #    if ct < 0.0001:
                        #        self.log.error(__name__ + ": " + security.print_obj())
                    exit()            
                elif self.accountDownloadEndstatus !='Done':
                    self.log.error(__name__ + ": " + 'ERROR in accountDonwload')                    
                else:   
                    self.log.error(__name__ + ": ERROR in retrieve hist data")
                    for reqid in self.returned_hist:
                        print self.returned_hist[reqid].status, reqid
                        if self.returned_hist[reqid].status!='Done':
                                self.log.error(__name__ + ": " + self.returned_hist[reqid].security.print_obj()\
                                                        +'.'+self.returned_hist[reqid].period)

                            #print self.returned_hist[reqid].security.symbol+'.' \
                            #     +self.returned_hist[reqid].security.currency+'.' \
                            #     +self.returned_hist[reqid].security.secType+'.'\
                            #     +self.returned_hist[reqid].period
            elif step == self.accountManagerState.WAIT_FOR_DAILY_PRICE_CALLBACK:
                self.log.error(__name__ + ": " + 'Time Limit Exceeded when \
                requesting historical daily data' + step, datetime.datetime.now() + \
                '\n' + 'The content of self.hist_daily: ')
                for security in self.data:
                    self.log.info(__name__ + ": " + str(self.data[security].hist_daily.head()))
#                if self.re_send < 3:    
#                    self.log.error(__name__ + ": " + 'Re-send req_daily_price_first')
#                    self.re_send += 1
#                    self.req_hist_price(endtime=datetime.datetime.now())
#                    self.set_timer()
#                else:
#                    self.log.error(__name__ + ": " + 'Re-send request three times, EXIT')
#                    exit()
            elif step == self.accountManagerState.WAIT_FOR_BAR_PRICE_CALLBACK:
                self.log.error(__name__ + ": " + 'Time Limit Exceeded when \
                requesting historical bar data' + \
                str(step) + str(datetime.datetime.now()))
                for security in self.data:
                    self.log.info(__name__ + ": " + str(self.data[security].hist_bar.head()))
#                if self.re_send < 3:    
#                    self.accountManagerState.set_state(
#                    self.accountManagerState.REQ_BAR_PRICE)
#                    self.log.error(__name__ + ": " + 'Re-send req_bar_price_first')
#                    self.re_send += 1
#                    self.set_timer()
#                else:
#                    self.log.error(__name__ + ": " + 'Re send request three times, EXIT')
#                    exit()
            elif step == self.accountManagerState.WAIT_FOR_UPDATE_PORTFOLIO_CALLBACK:
                self.log.error(__name__ + ": " + 'update account failed')
        
    ############### Next Valid ID ################### 
    def nextValidId(self, orderId):
        """
        IB API requires an orderId for every order, and this function obtains
        the next valid orderId. This function is called at the initialization 
        stage of the program and results are recorded in startingNextValidIdNumber,
        then the orderId is track by the program when placing orders
        """        
        self.log.info(__name__ + ": " + 'next valid order Id = ' + str(orderId))
        self.nextOrderId = orderId
        self.nextOrderId_Status = 'Done'
        
    ################## Request real time quotes   ########################
    def req_real_time_price(self):
        """
        Send request to IB server for real time market data
        """
        for security in self.data: 
            self.reqMktData(self.nextReqMktDataId, create_contract(security),
            '233',False) # Send market data requet to IB server
            time.sleep(0.1)
            security.req_real_time_price_id = self.nextReqMktDataId
            self.nextReqMktDataId += 1  # Prepare for next request

    ################# Request historical data ##########################################
    def req_hist_price(self, security, endtime, goback=None, barSize=None): 
        """
        Send request to IB server for real time market data
        """           
        #print 'req_hist_price', security.symbol+security.currency
        if goback==None:
            if barSize=='1 day':
                goback='1 Y'
            elif barSize=='1 min':
                goback='20000 S'
            elif barSize=='10 mins':
                goback='1 D'
            elif barSize=='1 hour':
                goback='30 D'
            elif barSize=='4 hours':
                goback='20 D'

            else:
                print 'req_hist_price cannot handle',barSize
                exit()
        # Submit request to IB
        if endtime.tzname()==None:
            req = datetime.datetime.strftime(endtime,"%Y%m%d %H:%M:%S") #datatime -> string
        else:
            endtime=endtime.astimezone(tz=pytz.utc)
            req = datetime.datetime.strftime(endtime,"%Y%m%d %H:%M:%S %Z") #datatime -> string
        #print req
        if security.secType=='STK' or security.secType=='FUT':
            self.reqHistoricalData(self.nextHistDataId, create_contract(security),
                                   req, goback, barSize, 'TRADES', 1, 1)
        elif security.secType=='CASH':
            self.reqHistoricalData(self.nextHistDataId, create_contract(security),
                                   req, goback, barSize, 'BID', 1, 1)
        # Record requst info
        self.returned_hist[self.nextHistDataId] = HistClass(security, barSize)
        self.returned_hist[self.nextHistDataId].status='submitted'# Record status

        # Others
        time.sleep(0.1)
        self.log.info(__name__ + ": " + "requesting hist data for " + security.symbol+'.' \
                                  + security.currency+'.'\
                                  + security.secType+'.'\
                                  + barSize)                    
        self.nextHistDataId += 1
            
    ################ order functions
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
        self.log.info(sec.symbol + ": " + orderAction + " " + str(amount))
    
        return self.nextOrderId
            
    ############# Quantopian compatible order functions ###################
    def order_quantopian(self, security, amount, style=MarketOrder()):       
        print 'place_order'
        if amount>0:  
            action='BUY'
            totalQuantity=amount
        elif amount<0:
            action='SELL'
            totalQuantity=-amount
        else:
            return -1
        security_order=create_order(action, totalQuantity, style)
        if security_order != None:
            cntrct=create_contract(security)
            self.placeOrder(self.my_next_valid_id, cntrct, security_order)
            print 'Request to',security_order.action,security_order.totalQuantity,'shares', cntrct.symbol+cntrct.currency,'id=',self.my_next_valid_id       
            self.context.portfolio.openOrderBook[self.my_next_valid_id] = \
                OrderClass(orderId=self.my_next_valid_id,
                    created=datetime.datetime.now(),
                    stop=style[1],
                    limit=style[2],
                    amount=security_order.totalQuantity,
                    sid=Security(cntrct.symbol+'.'+cntrct.currency),
                    status='PreSubmitted',
                    contract=cntrct,
                    order=security_order,
                    orderstate=None)
            self.my_next_valid_id=self.my_next_valid_id+1
            return self.my_next_valid_id-1
        else:
            print 'order_quantopian wrong serurity instance',security
            return -1

    def order_value_quantopian(self, security, value, style=MarketOrder()):
        print 'order_value_quantopian'
        import math        
        for ct in self.data:
            if same_security(security, ct):
                return self.order_quantopian(security, int(math.floor(value/self.data[ct].price)), style=style)
#        self.throwError('order_value_quantopian', 'could not find security')
        
    def order_percent_quantopian(self, security, percent, style=MarketOrder()):
        print 'order_percent_quantopian'
        import math        
        for ct in self.data:
            if same_security(security, ct):        
                return self.order_quantopian(security, int(math.floor(self.context.portfolio.portfolio_value/self.data[ct].price)) , style=style)
#        self.throwError('order_percent_quantopian', 'could not find security')


    def order_target_quantopian(self, security, amount, style=MarketOrder()):
        print 'place_order_target' 
        hold=self.how_many_I_am_holding(security) 
        #print amount,hold
        if amount!=hold:
            return self.order_quantopian(security, amount=amount-hold, style=style)
        else:
            return -1
    def order_target_value_quantopian(self, security, value, style=MarketOrder()):
        print 'place_order_target_value'
        import math             
        hold=self.how_many_I_am_holding(security, style='value')
        for ct in self.data:
            if same_security(security, ct):        
                return self.order_quantopian(security, int(math.floor((value-hold)/self.data[ct].price)) , style=style)
#        self.throwError('order_target_value_quantopian', 'could not find security')

    def order_target_percent_quantopian(self, security, percent, style=MarketOrder()):
        print 'place_order_percent_value'
        import math             
        hold=self.how_many_I_am_holding(security, style='portfolio_percentage')
        for ct in self.data:
            if same_security(security, ct):        
                return self.order_quantopian(security, int(math.floor((percent-hold)*self.context.portfolio.portfolio_value/self.data[ct].price)) , style=style)
#        self.throwError('order_target_percent_quantopian', 'could not find security')
                
    ################ Real time tick price data #########
    def update_DataClass(self, security, name, value):
        if (self.maxSaveTime > 0 and value > 0):
            currentTimeStamp = time.mktime(datetime.datetime.now().timetuple())
            newRow = [currentTimeStamp, value]
            tmp = getattr(self.data[security], name)
            tmp = np.vstack([tmp, newRow])
            # erase data points that go over the limit
            if (currentTimeStamp - tmp[0, 0]) > self.maxSaveTime:
                tmp = tmp[1:,:]
            setattr(self.data[security], name, tmp)
        
    def tickPrice(self, TickerId, tickType, price, canAutoExecute):
        """
        call back function of IB C++ API. This function will get tick prices
        """
        for security in self.data: 
            if security.req_real_time_price_id==TickerId:
                self.data[security].datetime=self.stime
                self.log.debug(__name__ + ', ' + str(TickerId) + ", " + MSG_TABLE[tickType]
                + ", " + str(security.symbol) + ", price = " + str(price))
                if tickType==1: #Bid price
                    self.data[security].bid_price = price
                    self.update_DataClass(security, 'bid_price_flow', price)
                elif tickType==2: #Ask price
                    self.data[security].ask_price = price
                    self.update_DataClass(security, 'ask_price_flow', price)                 
                elif tickType==4: #Last price
                    self.data[security].price = price
                    self.update_DataClass(security, 'last_price_flow', price)                
                elif tickType==6: #High daily price
                    self.data[security].daily_high_price=price
                elif tickType==7: #Low daily price
                    self.data[security].daily_low_price=price
                elif tickType==9: #last close price
                    self.data[security].daily_prev_close_price = price
                elif tickType == IBCpp.TickType.OPEN:
                    self.data[security].daily_open_price = price

                #if (self.stime_previous is None or self.stime - 
                #self.stime_previous > self.barSize):
                #    # the begining of the bar
                #    self.data[security].open_price=self.data[security].bid_price
                #    self.data[security].high=self.data[security].bid_price
                #    self.data[security].low=self.data[security].bid_price
                #else:
                #    if tickType==4 and price>self.data[security].high: #Bid price
                #        self.data[security].high=price
                #    if tickType==4 and price<self.data[security].low: #Bid price
                #        self.data[security].low=price
                        
    def tickSize(self, TickerId, tickType, size):
        """
        call back function of IB C++ API. This function will get tick size
        """
        for security in self.data: 
            if security.req_real_time_price_id==TickerId:
                self.log.debug(__name__ + ', ' + str(TickerId) + ", " + MSG_TABLE[tickType]
                + ", " + str(security.symbol) + ", size = " + str(size))
                self.data[security].datetime=self.stime
                if tickType == 0: # Bid Size
                    self.data[security].bid_size = size
                    self.update_DataClass(security, 'bid_size_flow', size)
                if tickType == 3: # Ask Size
                    self.data[security].ask_size = size
                    self.update_DataClass(security, 'ask_size_flow', size)  
                if tickType == 3: # Last Size
                    self.data[security].size = size
                    self.update_DataClass(security, 'last_size_flow', size)
                if tickType == 8: # Volume
                    self.data[security].volume = size
                    
    def tickString(self, tickerId, field, value):
        """
        IB C++ API call back function. The value variable contains the last 
        trade price and volume information. User show define in this function
        how the last trade price and volume should be saved
        RT_volume: 0 = trade timestamp; 1 = price_last, 
        2 = size_last; 3 = record_timestamp
        """
        # tickerId is indexed to data, so here we need to use data too
#        sec = self.data.keys()[tickerId]
        for security in self.data: 
            if security.req_real_time_price_id==tickerId:        
                currentTime = datetime.datetime.now(tz = self.USeasternTimeZone)
                valueSplit = value.split(';')
                if len(valueSplit) > 1 and float(valueSplit[1]) > 0:
                    timePy = float(valueSplit[2])/1000
                    priceLast = float(valueSplit[0]); sizeLast = float(valueSplit[1])
                    currentTimeStamp = time.mktime(datetime.datetime.now().timetuple())
                    self.log.debug(__name__ + ', ' + str(tickerId) + ", " 
                    + str(security.symbol) + ', ' + str(priceLast)
                    + ", " + str(sizeLast) + ', ' + str(timePy) + ', ' + str(currentTime))
                    # update price
                    newRow = [timePy, priceLast, sizeLast, currentTimeStamp]
                    priceSizeLastSymbol = self.data[security].RT_volume
                    priceSizeLastSymbol = np.vstack([priceSizeLastSymbol, newRow])
                    # erase data points that go over the limit
                    if (timePy - priceSizeLastSymbol[0, 0]) > self.maxSaveTime:
                        priceSizeLastSymbol = priceSizeLastSymbol[1:,:]
                    self.data[security].RT_volume = priceSizeLastSymbol
            
    ################ Historical data ################################
    def historicalData(self, reqId, date, price_open, price_high, price_low, price_close, volume, barCount, WAP, hasGaps):
        """
        call back function from IB C++ API
        return the historical data for requested security
        """
        #print reqId, date, price_open, price_high, price_low, price_close, volume, barCount, WAP, hasGaps              
        if 'finished' in str(date):
            self.returned_hist[reqId].status='Done'
            self.log.info(__name__ + ": " + "finished req hist data for "\
                                   + self.returned_hist[reqId].security.symbol+'.'\
                                  + self.returned_hist[reqId].security.currency+'.'\
                                  + self.returned_hist[reqId].security.secType+'.'\
                                  + self.returned_hist[reqId].period+' '\
                                  +str(len(self.returned_hist[reqId].hist))+' lines')
        else:
            if '  ' in date:                       
                date=datetime.datetime.strptime(date, '%Y%m%d  %H:%M:%S') # change string to datetime                        
            else:
                date=datetime.datetime.strptime(date, '%Y%m%d') # change string to datetime
            if date in self.returned_hist[reqId].hist.index:
                self.returned_hist[reqId].hist['open'][date]=price_open
                self.returned_hist[reqId].hist['high'][date]=price_high
                self.returned_hist[reqId].hist['low'][date]=price_low
                self.returned_hist[reqId].hist['close'][date]=price_close
                self.returned_hist[reqId].hist['volume'][date]=volume
            else:
                newRow = pd.DataFrame({'open':price_open,'high':price_high,
                                       'low':price_low,'close':price_close,
                                       'volume':volume}, index = [date])
                self.returned_hist[reqId].hist=self.returned_hist[reqId].hist.append(newRow)
            
    def req_real_time_price_check_end(self):
        """
        check if all securities have obtained price info
        """
        for security in self.data:
            for ct in [self.data[security].bid_price,self.data[security].ask_price]:                              
                if ct < 0.0001:
                    #print ct, 'not ready'
                    return False
        return True
        
    def req_hist_price_check_end(self):
        """
        check if all securities has obtained the requested historical data
        """
        for req_id in self.returned_hist:
            if self.returned_hist[req_id].status!='Done':
                return False
        return True                  
        
    def history_quantopian(self, bar_count, frequency, field, ffill=True):
        """
        function for requesting historical data similar to that defined in Quantopian
        historical daily data and historical bar data are already saved in self.data
        this function simple obtained the data from the already saved historical data
        """
        import pandas as pd
        if field=='open_price':
            inpt='open'
        elif field=='close_price' or field=='price':
            inpt='close'
        elif field=='high':
            inpt='high'
        elif field=='low':
            inpt='low'
        elif field=='volume':
            inpt='volume'
        else:
            self.log.error(__name__ + ": " + 'history_quantopian, field is not handled' + 
            str(field))
            exit()
            
        result=pd.DataFrame()
        for i, security in enumerate(self.data):
            if i==0:
                if frequency=='1d':
                    #print self.data[security].hist_daily[inpt][-bar_count:]
                    result=pd.DataFrame({security:self.data[security].hist['1 day'][inpt][-bar_count:]},index=self.data[security].hist['1 day'].index[-bar_count:])
                if frequency=='1m':
                    result=pd.DataFrame({security:self.data[security].hist['1 min'][inpt][-bar_count:]},index=self.data[security].hist['1 min'].index[-bar_count:])
            else:
                if frequency=='1d':
                    newColumn=pd.DataFrame({security:self.data[security].hist['1 day'][inpt][-bar_count:]},index=self.data[security].hist['1 day'].index[-bar_count:])
                if frequency=='1m':
                    newColumn=pd.DataFrame({security:self.data[security].hist['1 min'][inpt][-bar_count:]},index=self.data[security].hist['1 min'].index[-bar_count:])
                result=result.join(newColumn,how='outer')
        if ffill==True:
            result=result.fillna(method='ffill')
        return result
        
    def display_account_info(self):
        """
        print account info such as position values in format ways
        """
        self.log.info(__name__ + ": " + 'capital_used=' + str(self.context.portfolio.capital_used))
        self.log.info('cash=' + str(self.context.portfolio.cash))
        self.log.info('pnl=' + str(self.context.portfolio.pnl))
        self.log.info('portfolio_value=' + str(self.context.portfolio.portfolio_value))
        self.log.info('positions_value=' + str(self.context.portfolio.positions_value))
        self.log.info('returns=' + str(self.context.portfolio.returns))
        self.log.info('starting_cash=' + str(self.context.portfolio.starting_cash))
        self.log.info('start_date=' + str(self.context.portfolio.start_date))
        
        self.log.info('POSITIONS:')
        for ct in self.context.portfolio.positions:
            self.log.info(ct.symbol+ct.currency+ct.secType + ': ' + 
            str(self.context.portfolio.positions[ct]))
        self.log.info('OPEN ORDERS:')
        for ct in self.context.portfolio.openOrderBook:
            self.log.info(str(ct) + ': ' + 
            self.context.portfolio.openOrderBook[ct].contract.symbol + '.' + 
            self.context.portfolio.openOrderBook[ct].contract.currency + '.' + 
            self.context.portfolio.openOrderBook[ct].contract.secType + 
            str(self.context.portfolio.openOrderBook[ct].amount) + 
            self.context.portfolio.openOrderBook[ct].status)
            
    ############## Account management ####################
    def updateAccountValue(self, key, value, currency, accountName):
        """
        update account values such as cash, PNL, etc
        """
#        if (self.TRADE_DEBUG):
#            print 'updateAccountValue',key, value, currency, accountName
        if key == 'AvailableFunds':
            self.context.portfolio.cash=float(value)
        elif key == 'UnrealizedPnL':
            self.context.portfolio.pnl=float(value)
        elif key == 'NetLiquidation':
            self.context.portfolio.portfolio_value=float(value)
        elif key == 'GrossPositionValue':
            self.context.portfolio.positions_value=float(value)
        else:
            pass
            
    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
#        print 'updatePortfolio', contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName
#        print contract.currency
#        print contract.primaryExchange
#        print contract.secType
        for security in self.data:
            if security.symbol + security.currency == contract.symbol + contract.currency:
                self.context.portfolio.positions[security] = PositionClass(int(position),float(averageCost),float(marketPrice))
        
#    def updateAccountTime(self, timeStamp):
        #print 'updateAccountTime',timeStamp         
#        pass
    
    def accountDownloadEnd(self, accountName):
        self.log.info(__name__ + ": " + 'accountDownloadEnd' + str(accountName))
        if (self.context.portfolio.cash > 0 and self.context.portfolio.capital_used > 0):
            self.context.portfolio.capital_used=self.context.portfolio.positions_value-self.context.portfolio.pnl
            self.context.portfolio.returns=self.context.portfolio.portfolio_value/(self.context.portfolio.capital_used+self.context.portfolio.cash)-1.0
            self.context.portfolio.starting_cash=self.context.portfolio.capital_used+self.context.portfolio.cash
        self.accountDownloadEndstatus='Done'
        self.reqAccountUpdates(False, self.accountCode) 
 
    def accountSummary(self, reqID, account, tag, value, currency):
        self.log.info(__name__ + ": " + 'accountSummary' + str(reqID) + str(account) + str(tag) + 
        str(value) + str(currency))

    def accountSummaryEnd(self, reqId):
        self.log.info(__name__ + ": " + 'accountSummaryEnd' + str(reqId))

    def execDetails(self, reqId, contract, execution):
        pass        
        #print 'exeDetails',reqId, contract.symbol+contract.currency, execution.time,execution.execId,execution.orderId

    def commissionReport(self,commissionReport):
        pass        
        #print 'commissionReport',commissionReport.commission,commissionReport.execId
        

    def position(self, account, contract, position, price):
        """
        call back function of IB C++ API which updates the position of a contract
        of a account
        """
        self.log.info(__name__ + ": " + str(account) + str(contract.symbol) + '.' + 
        str(contract.currency) + ', ' + str(position) + ', ' + str(price))
        found = False
        for security in self.data:
            if contract.symbol==security.symbol and contract.secType==security.secType and contract.currency==security.currency:
                self.context.portfolio.positions[security]=PositionClass(amount=position,cost_basis=price,sid=security)
                found = True                
        if (not found):
            self.log.error(__name__ + ": " + 'Unexpected security' + contract.symbol 
            + '.' + str(contract.currency))
            #if contract.secType=='STK':            
            #    tp=Security(contract.symbol)
            #elif contract.secType=='CASH':
            #    tp=Security(contract.symbol+'.'+contract.currency)
            #self.context.portfolio.positions[tp]=PositionClass(amount=position, cost_basis=price)               

    #################### Order management ##########################
    def orderStatus(self,orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld):
        """
        call back function of IB C++ API which update status or certain order
        indicated by orderId
        """
        self.log.info(__name__ + ": " + str(orderId) + ", " + str(status) + ", "
        + str(filled) + ", " + str(remaining) + ", " + str(avgFillPrice))
        if orderId in self.context.portfolio.openOrderBook:     
            self.context.portfolio.openOrderBook[orderId].filled=filled
            self.context.portfolio.openOrderBook[orderId].remaining=remaining
            self.context.portfolio.openOrderBook[orderId].status=status
            if (self.context.portfolio.openOrderBook[orderId].parentOrderId 
            is not None and status == 'Filled'):
                if (self.context.portfolio.openOrderBook[orderId].stop is not None):
                    self.context.portfolio.openOrderBook[
                    self.context.portfolio.openOrderBook[orderId].parentOrderId].stop_reached = True
                    self.log.info(__name__ + ": " + "stop loss executed: " + 
                    self.context.portfolio.openOrderBook[orderId].contract.symbol)
                if (self.context.portfolio.openOrderBook[orderId].limit is not None):
                    self.context.portfolio.openOrderBook[
                    self.context.portfolio.openOrderBook[orderId].parentOrderId].limit_reached = True
                    self.log.info(__name__ + ": " + "stop loss executed: " +
                    self.context.portfolio.openOrderBook[orderId].contract.symbol)               
        
    def openOrder(self, orderId, contract, order, orderstate):
        """
        call back function of IB C++ API which updates the open orders indicated
        by orderId
        """
        self.log.info(__name__ + ": " + str(orderId) + ', ' + str(contract.symbol) + 
        '.' + str(contract.currency) + ', ' + str(order.action) + ', ' + 
        str(order.totalQuantity))
        if orderId in self.context.portfolio.openOrderBook:
            if self.context.portfolio.openOrderBook[orderId].contract!=contract:
                self.context.portfolio.openOrderBook[orderId].contract=contract                        
            if self.context.portfolio.openOrderBook[orderId].order!=order:
                self.context.portfolio.openOrderBook[orderId].order=order                        
            if self.context.portfolio.openOrderBook[orderId].orderstate!=orderstate:
                self.context.portfolio.openOrderBook[orderId].orderstate=orderstate                        
            self.context.portfolio.openOrderBook[orderId].status=orderstate.status            
        else:
            self.context.portfolio.openOrderBook[orderId] = \
                OrderClass(orderId=orderId,
                           created=datetime.datetime.now(),
                    stop=(lambda x: x if x<100000 else None)(order.auxPrice),
                    limit=(lambda x: x if x<100000 else None)(order.lmtPrice),
                    amount=order.totalQuantity,
                    commission=(lambda x: x if x<100000 else None)(orderstate.commission),
                    sid=Security(contract.symbol+'.'+contract.currency),
                    status=orderstate.status,
                    contract=contract, order=order,
                    orderstate=orderstate)
                    
    def cancel_order_quantopian(self, order):
        """
        function to cancel orders similar to that defined in Quantopian
        """
        if isinstance(order, OrderClass):
            self.cancelOrder(order.orderId)
        else:
            self.cancelOrder(int(order))

    def get_open_order_quantopian(self, sid=None):
        """
        function to get open orders similar to that defined in Quantopian
        """
        if sid==None:
            result={}
            for ct in self.context.portfolio.openOrderBook:
                result[self.context.portfolio.openOrderBook[ct].sid]=self.context.portfolio.openOrderBook[ct]
            return result
        else:
            result={}            
            for ct in self.context.portfolio.openOrderBook:
                if same_security(self.context.portfolio.openOrderBook[ct].sid,sid):
                    result[self.context.portfolio.openOrderBook[ct].sid]=self.context.portfolio.openOrderBook[ct]
            return result
        
    def how_many_I_am_holding(self, security, style='shares'):
        """
        return the current holdings of a security, in styles of shares, value
        or percentage
        """
        for ct in self.context.portfolio.positions:
            if same_security(ct,security):
                if style=='shares':
                    return self.context.portfolio.positions[ct].amount
                if style=='value':    
                    return self.context.portfolio.positions[ct].amount*self.context.portfolio.positions[ct].last_sale_price
                if style=='portfolio_percentage':
                    if self.context.portfolio.portfolio_value > 0.00001:
#                        self.throwError('how_many_I_am_holding','Zero portfolio value')
                        return self.context.portfolio.positions[ct].last_sale_price / self.context.portfolio.portfolio_value
        return 0

    def how_many_is_pending(self, security):
        """
        return the number of shares that is still pending for transaction
        """
        amount_pending=0
        for orderId in self.context.portfolio.openOrderBook:
            if     self.context.portfolio.openOrderBook[orderId].contract.symbol==security.symbol \
               and self.context.portfolio.openOrderBook[orderId].contract.currency==security.currency \
               and self.context.portfolio.openOrderBook[orderId].contract.secType==security.secType :
                   amount_pending=amount_pending+self.context.portfolio.openOrderBook[orderId].order.totalQuantity
        return amount_pending

    ############### Other ################
#    def throwError(func, message):
#        if message=='Zero portfolio value':
#            print func, message,'EXIT'; exit()
#        if message=='could not find security':
#            print func, message,'EXIT'; exit()
            
    def get_datetime_quantopian(self, timezone=None):
        """
        function to get the current datetime of IB system similar to that
        defined in Quantopian
        """
        import pytz
        time_temp=self.stime.replace(tzinfo = self.USeasternTimeZone)
        if timezone==None:
            return time_temp.astimezone(pytz.UTC)
        else:
            return time_temp.astimezone(timezone)

if __name__ == "__main__":
    port = 7496; clientID = 1
    c = IBAccountManager()  # create a client object
    c.setup();      # additional setup. It's optional.
    c.connect("", port, clientID) # you need to connect to the server before you do anything.
#    c.reqCurrentTime()
#    while(1):
#        if (c.stime is not None and c.stime_previous is None):
#            c.stime_previous = c.stime
#            print "current system time: ", c.stime, datetime.datetime.now(tz = c.USeasternTimeZone)
#        c.processMessages()       # put this function into infinit loop. A better way is to put it into a new thread.     