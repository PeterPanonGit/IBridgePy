import IBridgePy  # You need to link/copy IBridgePy.pyd to the same directory 
import pandas as pd
import datetime
import time



from quantopian import Security,ContextClass,PositionClass, HistClass, create_contract, MarketOrder,create_order, OrderClass
from quantopian import same_security

class IBtrading(IBridgePy.IBClient) :  #  define a new client class. All client classes are recommended to derive from IBClient unless you have special need.  
    
    def setup(self):
        self.state = "init"
        self.machine_state='init_first_step'
        self.data={}
        self.accountDownloadEndstatus='na'
        self.stime_previous=datetime.datetime.now()
        self.stime=datetime.datetime.now()
        self.context = ContextClass()
        self.last_message='na'

    def display(self,message):
        if message!=self.last_message:
            print message, datetime.datetime.now()
            self.last_message=message
            
    def error(self, errorId, errorCode, errorString):
        if errorCode<2000:
            print 'errorId = ' + str(errorId), 'errorCode = ' + str(errorCode)
            print 'error message: ' + errorString

    def currentTime(self, tm):
        self.stime= datetime.datetime.fromtimestamp(float(str(tm)))
        

        
    ######################   SUPPORT ############################33

    timer_start=datetime.datetime.now()
    re_send=0
    def set_timer(self):
        self.timer_start=datetime.datetime.now()
    def check_timer(self, step,limit=10):
        timer_now=datetime.datetime.now()
        change=(timer_now-self.timer_start).total_seconds()
        if change>limit:
            if step=='init_second_step':
                if self.update_all_positions_status != 'Done':
                    print 'Something is not right in',step,datetime.datetime.now()
                    print 'The content of self.openOrders'
                    print self.openOrders
                    print 'EXIT'
                    print exit()
                if self.nextValidId_status !='Done':
                    print 'Something is not right in',step,datetime.datetime.now()
                    print 'self.nextValidId_status=',self.nextValidId_status
                    print 'EXIT'
                    print exit()
                if self.request_real_time_price_status != 'Done': 
                    self.display='Server is not open'
                    time.sleep(1)

            elif step=='second_step':
                print 'Something is not right in',step,datetime.datetime.now()
                print 'The content of self.hist_daily'
                for security in self.data:
                    print self.data[security].hist_daily   
                if self.re_send<3:    
                    print 'Re-send req_daily_price_first'
                    self.re_send=self.re_send+1
                    self.req_hist_price(endtime=datetime.datetime.now())
                    self.set_timer()
                else:
                    print 'Re send request three times, EXIT'
                    exit()
            elif step=='wake_up_second_step':
                print 'Something is not right in',step,datetime.datetime.now()
                print 'The content of self.req_hist_status'
                print self.req_hist_status
                print 'The content of self.hist'
                print self.hist
                self.machine_state='wake_up_first_step'
                print 'SPEICIAL ERROR Handling'                   

            elif step=='running_second_step':
                print 'Something is not right in',step,datetime.datetime.now()
                print 'The content of self.check_results'
                print self.check_results
                print 'EXIT'                    
                exit()
            elif step=='friday_check_second_step':
                print 'Something is not right in',step,datetime.datetime.now()
                print 'The content of self.check_results'
                print self.check_results
                print 'EXIT'                    
                exit()

            elif step=='req_minute_price_second':
                print 'Something is not right in',step,datetime.datetime.now()
                for security in self.data:
                    print self.data[security].hist_minute
                if self.re_send<3:    
                    self.machine_state='req_minute_price_first'
                    print 'Re-send req_minute_price_first'
                    self.re_send=self.re_send+1
                else:
                    print 'Re send request three times, EXIT'
                    exit()
            elif step=='update_portfolio_second':
                self.display('update account failed')
        
    ############### Next Valid ID ################### 
    my_next_valid_id=0
    nextValidId_status='none'
    def nextValidId(self, orderId):
        #print 'next valid order Id = ' + str(orderId)
        self.my_next_valid_id = orderId
        self.nextValidId_status='Done'  
        
    ################## Request real time quotes   ########################
    def req_real_time_price(self):
        for security in self.data: 
            if security.secType=='CASH':
                self.reqMktData(self.my_next_valid_id,create_contract(security),'233',False) # Send requet to IB server
                security.req_real_time_price_id=self.my_next_valid_id
                self.my_next_valid_id=self.my_next_valid_id+1  # Prepare for next request                      
            
    def tickPrice(self, TickerId, tickType, price, canAutoExecute):
        #print  TickerId, tickType, price, canAutoExecute     
        for security in self.data: 
            if security.req_real_time_price_id==TickerId:
                self.data[security].datetime=self.stime
                if tickType==1: #Bid price
                    self.data[security].bid_price=price
                elif tickType==2: #Ask price
                    self.data[security].ask_price=price
                elif tickType==4: #Last price
                    pass
                elif tickType==6: #High daily price
                    self.data[security].daily_high_price=price
                elif tickType==7: #Low daily price
                    self.data[security].daily_low_price=price
                elif tickType==9: #last close price
                    pass
                else:
                    print 'tickPrice ERROR',tickType;exit()

                if int(self.stime_previous.second)!=0 and int(self.stime.second)==0: # the begining of the bar
                    self.data[security].open_price=self.data[security].bid_price
                    self.data[security].high=self.data[security].bid_price
                    self.data[security].low=self.data[security].bid_price
                else:
                    if tickType==1 and price>self.data[security].high: #Bid price
                        self.data[security].high=price
                    if tickType==1 and price<self.data[security].low: #Bid price
                        self.data[security].low=price

    def req_real_time_price_check_end(self):
        for security in self.data:
            for ct in [self.data[security].bid_price,self.data[security].ask_price]:                              
                if ct<0.0001:
                    #print ct, 'not ready'
                    return False
        return True
            
    ################# Request historical data ##########################################
    returned_hist= {}
    def req_hist_price(self, endtime, goback='1 Y', barSize='1 day'):               
        for security in self.data:
            #print 'req_hist_price', endtime,self.stime, security.symbol
            self.returned_hist[security]=HistClass()
            req=datetime.datetime.strftime(endtime,"%Y%m%d %H:%M:%S") #datatime -> string
            self.reqHistoricalData(self.my_next_valid_id, create_contract(security),req, goback, barSize, 'BID', 1, 1)
            self.returned_hist[security].status='submitted'# Record status
            self.returned_hist[security].req_id=self.my_next_valid_id                     
            self.my_next_valid_id=self.my_next_valid_id+1

    def historicalData(self, reqId, date, price_open, price_high, price_low, price_close, volume, barCount, WAP, hasGaps):
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
                        newRow = pd.DataFrame({'open':price_open,'high':price_high,'low':price_low,'close':price_close,'volume':volume}, index = [date])
                        self.returned_hist[security].hist=self.returned_hist[security].hist.append(newRow)

    def req_hist_price_check_end(self):    
        for security in self.returned_hist:
            if self.returned_hist[security].status!='Done':
                return False
        return True                  
        
    def updateAccountValue(self, key, value, currency, accountName):
        #print 'updateAccountValue',key, value, currency, accountName
               
        if key=='AvailableFunds':
            self.context.portfolio.cash=float(value)
        elif key=='UnrealizedPnL':
            self.context.portfolio.pnl=float(value)
        elif key=='NetLiquidation':
            self.context.portfolio.portfolio_value=float(value)
        elif key=='GrossPositionValue':
            self.context.portfolio.positions_value=float(value)
        else:
            pass
            
            
    def updatePortfolio(self, contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName):
        #print 'updatePortfolio', contract, position, marketPrice, marketValue, averageCost, unrealizedPNL, realizedPNL, accountName
        #print contract.currency
        #print contract.primaryExchange
        #print contract.secType
        #for security in self.data:
        #    if security.symbol+security.currency==contract.symbol+contract.currency:
        #        self.context.portfolio.positions[security]=PositionClass(int(position),float(averageCost),float(marketPrice))
        pass
        
        
    def updateAccountTime(self, timeStamp):
        #print 'updateAccountTime',timeStamp         
        pass
    
    def accountDownloadEnd(self, accountName):
        print 'accountDownloadEnd', accountName
        if (self.context.portfolio.cash > 0 and self.context.portfolio.capital_used > 0):
            self.context.portfolio.capital_used=self.context.portfolio.positions_value-self.context.portfolio.pnl
            self.context.portfolio.returns=self.context.portfolio.portfolio_value/(self.context.portfolio.capital_used+self.context.portfolio.cash)-1.0
            self.context.portfolio.starting_cash=self.context.portfolio.capital_used+self.context.portfolio.cash
        self.accountDownloadEndstatus='Done'
        self.reqAccountUpdates(False,'All') 
 
    def accountSummary(self, reqID, account, tag, value, currency):
        print 'accountSummary', reqID, account, tag, value, currency

    def accountSummaryEnd(self, reqId):
        print 'accountSummaryEnd', reqId   

    def execDetails(self, reqId, contract, execution):
        pass        
        #print 'exeDetails',reqId, contract.symbol+contract.currency, execution.time,execution.execId,execution.orderId

    def commissionReport(self,commissionReport):
        pass        
        #print 'commissionReport',commissionReport.commission,commissionReport.execId
        

    def position(self, account, contract, position,price):
        #print 'position',account, contract.symbol+'.'+contract.currency, position,price
        found=False        
        for security in self.data:
            if contract.symbol==security.symbol and contract.secType==security.secType and contract.currency==security.currency:
                self.context.portfolio.positions[security]=PositionClass(amount=position,cost_basis=price,sid=security)
                found=True                
        if found==False:
            pass            
            #print 'Unexpected security',contract.symbol+'.'+contract.currency
            #if contract.secType=='STK':            
            #    tp=Security(contract.symbol)
            #elif contract.secType=='CASH':
            #    tp=Security(contract.symbol+'.'+contract.currency)
            #self.context.portfolio.positions[tp]=PositionClass(amount=position, cost_basis=price)               

                 
    def orderStatus(self,orderId, status, filled, remaining, avgFillPrice, permId, parentId, lastFillPrice, clientId, whyHeld):
        if orderId in self.context.portfolio.openOrderBook:     
            self.context.portfolio.openOrderBook[orderId].filled=filled
            self.context.portfolio.openOrderBook[orderId].remaining=remaining
            self.context.portfolio.openOrderBook[orderId].status=status
        
    def openOrder(self, orderId, contract, order, orderstate):
        #print 'openOrder',orderId, contract.symbol+'.'+contract.currency, order.action,order.totalQuantity,orderstate.commission, orderstate.commissionCurrency,orderstate.maxCommission, orderstate.minCommission,orderstate.warningText      
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
        self.throwError('order_value_quantopian', 'could not find security')
        
    def order_percent_quantopian(self, security, percent, style=MarketOrder()):
        print 'order_percent_quantopian'
        import math        
        for ct in self.data:
            if same_security(security, ct):        
                return self.order_quantopian(security, int(math.floor(self.context.portfolio.portfolio_value/self.data[ct].price)) , style=style)
        self.throwError('order_percent_quantopian', 'could not find security')


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
        self.throwError('order_target_value_quantopian', 'could not find security')

    def order_target_percent_quantopian(self, security, percent, style=MarketOrder()):
        print 'place_order_percent_value'
        import math             
        hold=self.how_many_I_am_holding(security, style='portfolio_percentage')
        for ct in self.data:
            if same_security(security, ct):        
                return self.order_quantopian(security, int(math.floor((percent-hold)*self.context.portfolio.portfolio_value/self.data[ct].price)) , style=style)
        self.throwError('order_target_percent_quantopian', 'could not find security')

    def cancel_order_quantopian(self, order):
        if isinstance(order, OrderClass):
            self.cancelOrder(order.orderId)
        else:
            self.cancelOrder(int(order))

    def get_open_order_quantopian(self, sid=None):
        if sid==None:
            result={}
            for ct in self.context.portfolio.openOrderBook:
                result[self.context.portfolio.openOrderBook[ct].sid] = \
                self.context.portfolio.openOrderBook[ct]
            return result
        else:
            result={}            
            for ct in self.context.portfolio.openOrderBook:
                if same_security(self.context.portfolio.openOrderBook[ct].sid,sid):
                    result[self.context.portfolio.openOrderBook[ct].sid] = \
                    self.context.portfolio.openOrderBook[ct]
            return result

    def get_datetime_quantopian(self, timezone=None):
        import pytz
        time_temp=self.stime.replace(tzinfo=pytz.timezone('US/Eastern'))
        if timezone==None:
            return time_temp.astimezone(pytz.UTC)
        else:
            return time_temp.astimezone(timezone)

    def history_quantopian(self, bar_count, frequency, field, ffill=True):
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
            print 'history_quantopian, field is not handled',field
            exit()
            
        result=pd.DataFrame()
        for i, security in enumerate(self.data):
            if i==0:
                if frequency=='1d':
                    #print self.data[security].hist_daily[inpt][-bar_count:]
                    result=pd.DataFrame({security.symbol+'.'+security.currency+'.'+security.secType:self.data[security].hist_daily[inpt][-bar_count:]},index=self.data[security].hist_daily.index[-bar_count:])
                if frequency=='1m':
                    result=pd.DataFrame({security.symbol+'.'+security.currency+'.'+security.secType:self.data[security].hist_minute[inpt][-bar_count:]},index=self.data[security].hist_minute.index[-bar_count:])
            else:
                if frequency=='1d':
                    newColumn=pd.DataFrame({security.symbol+'.'+security.currency+'.'+security.secType:self.data[security].hist_daily[inpt][-bar_count:]},index=self.data[security].hist_daily.index[-bar_count:])
                if frequency=='1m':
                    newColumn=pd.DataFrame({security.symbol+'.'+security.currency+'.'+security.secType:self.data[security].hist_minute[inpt][-bar_count:]},index=self.data[security].hist_minute.index[-bar_count:])
                result=result.join(newColumn,how='outer')
        if ffill==True:
            result=result.fillna(method='ffill')
        return result
        
    def how_many_I_am_holding(self, security, style='shares'):
        for ct in self.context.portfolio.positions:
            if same_security(ct,security):
                if style=='shares':
                    return self.context.portfolio.positions[ct].amount
                if style=='value':    
                    return self.context.portfolio.positions[ct].amount*self.context.portfolio.positions[ct].last_sale_price
                if style=='portfolio_percentage':
                    if self.context.portfolio.portfolio_value<=0.00001:
                        self.throwError('how_many_I_am_holding','Zero portfolio value')
                    return self.context.portfolio.positions[ct].last_sale_price/self.context.portfolio.portfolio_value
        return 0

    def how_many_is_pending(self, security):
        amount_pending=0
        for orderId in self.context.portfolio.openOrderBook:
            if     self.context.portfolio.openOrderBook[orderId].contract.symbol==security.symbol \
               and self.context.portfolio.openOrderBook[orderId].contract.currency==security.currency \
               and self.context.portfolio.openOrderBook[orderId].contract.secType==security.secType :
                   amount_pending=amount_pending+self.context.portfolio.openOrderBook[orderId].order.totalQuantity
        return amount_pending           

            
    def throwError(func, message):
        if message=='Zero portfolio value':
            print func, message,'EXIT'; exit()
        if message=='could not find security':
            print func, message,'EXIT'; exit()
            
            
#################################### Not critical ##############
    def display_account_info(self):
        print 'capital_used=',self.context.portfolio.capital_used
        print 'cash=',self.context.portfolio.cash
        print 'pnl=',self.context.portfolio.pnl
        print 'portfolio_value=',self.context.portfolio.portfolio_value
        print 'positions_value=',self.context.portfolio.positions_value
        print 'returns=',self.context.portfolio.returns
        print 'starting_cash=',self.context.portfolio.starting_cash
        print 'start_date=',self.context.portfolio.start_date
        
        print 'POSITIONS'
        for ct in self.context.portfolio.positions:
            print ct.symbol+ct.currency+ct.secType, self.context.portfolio.positions[ct]
        print 'OPEN ORDERS'
        for ct in self.context.portfolio.openOrderBook:
            print ct, self.context.portfolio.openOrderBook[ct].contract.symbol+'.'+self.context.portfolio.openOrderBook[ct].contract.currency+'.'+self.context.portfolio.openOrderBook[ct].contract.secType,self.context.portfolio.openOrderBook[ct].amount,self.context.portfolio.openOrderBook[ct].status



            
            