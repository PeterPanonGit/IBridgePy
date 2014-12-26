# -*- coding: utf-8 -*-

import datetime, time
import pandas as pd
import logging
import os

from IBridgePy.IBridgePyBasicLib.quantopian import Security, ContextClass, PositionClass, \
HistClass, create_contract, MarketOrder, create_order, OrderClass, same_security, \
DataClass
import IBCpp
from BasicPyLib.FiniteState import FiniteStateClass
from BasicPyLib.simpleLogger import SimpleLoggerClass

class IBAccountManager(IBCpp.IBClient):
    """
    IBAccountManager manages the account, order, and historical data information
    from IB. These information are needed by all kinds of traders.
    stime: system time obtained from IB
    """
    def setup(self, PROGRAM_DEBUG = False, TRADE_DEBUG = True,
              USeasternTimeZone = None, accountCode = 'ALL', minTick = 0.01, 
              port = 7496, clientId = 1):
        """
        initialize the IBAccountManager. We don't do __init__ here because we don't
        want to overwrite parent class IBCpp.IBClient's __init__ function
        """
        # timezone info passed from MarketManager
        self.USeasternTimeZone = USeasternTimeZone
        
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
        self.accountDownloadEndstatus='na'
        self.stime_previous = None
        self.stime = datetime.datetime.now(tz = self.USeasternTimeZone)
        self.context = ContextClass()
        self.context.USeasternTimeZone = self.USeasternTimeZone
        self.last_message='na'
        self.minTick = minTick
        
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
        self.log = SimpleLoggerClass('TraderLog_' + self.todayDateStr + '.txt')
        self.log.info(__name__ + ": " + "accountCode: " + str(self.accountCode))
        
        # setup IB's log file and message level
        self.logFileName = "IB_system_log.txt"
        self.logOn()
        self.echo = True
        self.addMessageLevel(IBCpp.MsgLevel.SYSERR)
        self.addMessageLevel(IBCpp.MsgLevel.IBINFO)
        self.log.info(__name__ + ": " + 
        "IB message level: " + "{0:b}".format(self.getMessageLevel()))
            
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
        
    def check_timer(self, step, limit = 10):
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
                    self.set_timer()
            elif step == self.accountManagerState.WAIT_FOR_DAILY_PRICE_CALLBACK:
                self.log.error(__name__ + ": " + 'Time Limit Exceeded when \
                requesting historical daily data' + step, datetime.datetime.now() + \
                '\n' + 'The content of self.hist_daily: ')
                for security in self.data:
                    self.log.info(__name__ + ": " + str(self.data[security].hist_daily.head()))
                if self.re_send < 3:    
                    self.log.error(__name__ + ": " + 'Re-send req_daily_price_first')
                    self.re_send += 1
                    self.req_hist_price(endtime=datetime.datetime.now())
                    self.set_timer()
                else:
                    self.log.error(__name__ + ": " + 'Re-send request three times, EXIT')
                    exit()
            elif step == self.accountManagerState.WAIT_FOR_BAR_PRICE_CALLBACK:
                self.log.error(__name__ + ": " + 'Time Limit Exceeded when \
                requesting historical bar data' + \
                str(step) + str(datetime.datetime.now()))
                for security in self.data:
                    self.log.info(__name__ + ": " + str(self.data[security].hist_bar.head()))
                if self.re_send < 3:    
                    self.accountManagerState.set_state(
                    self.accountManagerState.REQ_BAR_PRICE)
                    self.log.error(__name__ + ": " + 'Re-send req_bar_price_first')
                    self.re_send += 1
                    self.set_timer()
                else:
                    self.log.error(__name__ + ": " + 'Re send request three times, EXIT')
                    exit()
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
    def req_hist_price(self, endtime, goback='1 Y', barSize='1 day'): 
        """
        Send request to IB server for real time market data
        """           
        for security in self.data:
            #print 'req_hist_price', endtime,self.stime, security.symbol
            self.returned_hist[security] = HistClass()
            req = datetime.datetime.strftime(endtime,"%Y%m%d %H:%M:%S") #datatime -> string
            self.reqHistoricalData(self.nextHistDataId, create_contract(security),
                                   req, goback, barSize, 'BID', 1, 1)
            time.sleep(0.1)
            self.returned_hist[security].status='submitted'# Record status
            self.returned_hist[security].req_id = self.nextHistDataId                     
            self.nextHistDataId += 1

    ################ Real time tick data without volume info #########
    def tickPrice(self, TickerId, tickType, price, canAutoExecute):
        """
        call back function of IB C++ API. This function will get tick prices and 
        it is up to the specific Trader class to decide how to save the data
        """
        for security in self.data: 
            if security.req_real_time_price_id==TickerId:
                self.data[security].datetime=self.stime
                if tickType==1: #Bid price
                    self.data[security].bid_price=price
                elif tickType==2: #Ask price
                    self.data[security].ask_price=price
                elif tickType==4: #Last price
                    self.data[security].price = price
                elif tickType==6: #High daily price
                    self.data[security].daily_high_price=price
                elif tickType==7: #Low daily price
                    self.data[security].daily_low_price=price
                elif tickType==9: #last close price
                    pass

                if (self.stime_previous is None or self.stime - 
                self.stime_previous > self.barSize):
                    # the begining of the bar
                    self.data[security].open_price=self.data[security].bid_price
                    self.data[security].high=self.data[security].bid_price
                    self.data[security].low=self.data[security].bid_price
                else:
                    if tickType==4 and price>self.data[security].high: #Bid price
                        self.data[security].high=price
                    if tickType==4 and price<self.data[security].low: #Bid price
                        self.data[security].low=price
                        
    ################ Historical data ################################
    def historicalData(self, reqId, date, price_open, price_high, price_low, price_close, volume, barCount, WAP, hasGaps):
        """
        call back function from IB C++ API
        return the historical data for requested security
        """
        #print reqId, date, price_open, price_high, price_low, price_close, volume, barCount, WAP, hasGaps
        for security in self.returned_hist:            
            if self.returned_hist[security].req_id==reqId:              
                if 'finished' in str(date):
                    self.returned_hist[security].status='Done'
                else:
                    if '  ' in date:                       
                        date=datetime.datetime.strptime(date, '%Y%m%d  %H:%M:%S') # change string to datetime                        
                    else:
                        date=datetime.datetime.strptime(date, '%Y%m%d') # change string to datetime
                    if date in self.returned_hist[security].hist.index:
                        self.returned_hist[security].hist['open'][date]=price_open
                        self.returned_hist[security].hist['high'][date]=price_high
                        self.returned_hist[security].hist['low'][date]=price_low
                        self.returned_hist[security].hist['close'][date]=price_close
                        self.returned_hist[security].hist['volume'][date]=volume
                    else:
                        newRow = pd.DataFrame({'open':price_open,'high':price_high,
                                               'low':price_low,'close':price_close,
                                               'volume':volume}, index = [date])
                        self.returned_hist[security].hist=self.returned_hist[security].hist.append(newRow)

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
        for security in self.returned_hist:
            if self.returned_hist[security].status!='Done':
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
                    result=pd.DataFrame({security:self.data[security].hist_daily[inpt][-bar_count:]},index=self.data[security].hist_daily.index[-bar_count:])
                if frequency=='1m':
                    result=pd.DataFrame({security:self.data[security].hist_bar[inpt][-bar_count:]},index=self.data[security].hist_bar.index[-bar_count:])
            else:
                if frequency=='1d':
                    newColumn=pd.DataFrame({security:self.data[security].hist_daily[inpt][-bar_count:]},index=self.data[security].hist_daily.index[-bar_count:])
                if frequency=='1m':
                    newColumn=pd.DataFrame({security:self.data[security].hist_bar[inpt][-bar_count:]},index=self.data[security].hist_bar.index[-bar_count:])
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
