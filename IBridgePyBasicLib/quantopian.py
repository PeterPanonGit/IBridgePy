
import datetime
import pandas as pd
import numpy as np
import os
from BasicPyLib.Printable import PrintableClass

def symbol(s1):
    return Security(s1)
    
def symbols(*args): 
    ls=[]
    for item in args:
        ls.append(Security(item))
    return ls       

def create_contract(security):
    import IBCpp
    contract = IBCpp.Contract()
    contract.symbol = security.symbol
    contract.secType = security.secType
    contract.exchange = security.exchange
    contract.currency = security.currency       
    contract.primaryExchange = security.primaryExchange
    if security.secType=='FUT':
        contract.expiry = security.expiry       

    return contract 

def create_order(action,amount,style): 
    import IBCpp
    orderType,stop_price,limit_price,exchange=style
    order = IBCpp.Order()
    order.action = action      # BUY, SELL
    order.totalQuantity = amount
    order.orderType =  orderType  #LMT, MKT, STP
    order.tif='GTC'
    order.transmit = True 
    if orderType=='MKT':
        return order
    elif orderType=='LMT':    
        order.lmtPrice=limit_price
        return order
    elif orderType=='STP':
        order.auxPrice=stop_price
        return order 
    elif orderType=='STP LMT':
        order.lmtPrice=limit_price
        order.auxPrice=stop_price
        return order
    else:
        print 'Cannot handle order type:',orderType
        return None        

def same_security(se_1, se_2):
    if se_1.symbol+se_1.currency+se_1.secType==se_2.symbol+se_2.currency+se_2.secType:
        return True
    else:
        return False

def MarketOrder(exchange='SMART'):
    orderType='MKT'
    return (orderType,None,None,exchange)

def StopOrder(stop_price, exchange='SMART'):
    orderType='STP'
    return (orderType,stop_price,None,exchange)
    
def LimitOrder(limit_price, exchange='SMART'):
    orderType='LMT'
    return (orderType,None,limit_price,exchange)

def StopLimitOrder(limit_price, stop_price, exchange='SMART'):
    orderType='STP LMT'
    return (orderType,stop_price,limit_price,exchange)


############## Quantopian compatible data structures
stockList = pd.read_csv(os.path.join(os.path.dirname(os.path.dirname(__file__)),
'all_US_Stocks.csv'))

class Security(PrintableClass):
    def __init__(self, symbol, sid=0, security_name=None, security_start_date=None,security_end_date=None):

        self.sid=sid
        self.security_name=security_name
        self.security_start_date = None
        self.security_end_date=datetime.datetime.now()
        self.nextReqMktDataId = 0

        self.secType = symbol.split('.')[0]
        self.symbol=symbol.split('.')[1]            
        self.currency = symbol.split('.')[2]

        if self.secType=='CASH': # 'CASH.EUR.USD'
            self.exchange = 'IDEALPRO'
            self.primaryExchange = 'IDEALPRO'
        elif self.secType == 'FUT': # 'FUT.ES.USD.201503'
            self.exchange = 'GLOBEX'
            self.primaryExchange='GLOBEX'
            self.expiry=symbol.split('.')[3]
        elif self.secType == 'STK':
            self.secType='STK'
            self.exchange = 'SMART'
            tmp_df = stockList[stockList['Symbol'] == symbol]
            if (tmp_df.shape[0] > 0):
                self.primaryExchange = tmp_df['primaryExchange'].values[0]
                self.currency = tmp_df['Currency'].values[0]
                self.security_name = tmp_df['Name'].values[0]
                self.security_start_date = tmp_df['IPOyear'].values[0]
            else:
                self.primaryExchange = 'NYSE'
                self.currency = 'USD' 
                
class ContextClass(PrintableClass):
    def __init__(self):
        self.portfolio = PortofolioClass()
        

class PortofolioClass(PrintableClass):
    def __init__(self, capital_used = 0.0, cash = 0.0, pnl = 0.0, positions = {}, openOrderBook={}, 
                 portfolio_value = 0.0, positions_value = 0.0, returns = 0.0, 
                 starting_cash = 0.0, start_date = datetime.datetime.now()):
        self.capital_used = capital_used
        self.cash = cash
        self.pnl = pnl
        self.positions = positions
        self.openOrderBook= openOrderBook
        self.portfolio_value = portfolio_value
        self.positions_value = positions_value
        self.returns = returns
        self.starting_cash = starting_cash
        self.start_date = start_date
        
class PositionClass(PrintableClass):
    def __init__(self, amount=0, cost_basis=None, last_sale_price=None, sid=None):
        self.amount = amount
        self.cost_basis=cost_basis
        self.last_sale_price = last_sale_price
        self.sid=sid

        
      
class DataClass(PrintableClass):
    def __init__(self,
                 datetime=datetime.datetime(2000,01,01,00,00),
                 price = None,
                 open_price = None,
                 close_price = None,
                 high = None,
                 low =None,
                 volume = 0,
                 hist_frame=['1 day']):        
        self.datetime=datetime # Quatopian
        self.price=price # Quatopian
        self.size = None
        self.open_price=open_price # Quatopian
        self.close_price=close_price # Quatopian
        self.high = high # Quatopian
        self.low = low # Quatopian
        self.volume = volume # Quatopian
        self.daily_open_price = None
        self.daily_high_price = None
        self.daily_low_price = None
        self.daily_prev_close_price = None
        self.bid_price = None
        self.ask_price = None
        self.bid_size = None
        self.ask_size = None
        self.hist={}
        for frame in hist_frame:
            self.hist[frame]=pd.DataFrame()
        # 0 = record_timestamp
        self.bid_price_flow = np.zeros(shape = (0,2))
        self.ask_price_flow = np.zeros(shape = (0,2))
        self.last_price_flow = np.zeros(shape = (0,2))
        self.bid_size_flow = np.zeros(shape = (0,2))
        self.ask_size_flow = np.zeros(shape = (0,2))
        self.last_size_flow = np.zeros(shape = (0,2))        
        # 0 = trade timestamp; 1 = price_last; 2 = size_last; 3 = record_timestamp
        self.RT_volume = np.zeros(shape = (0,4))
        
    def update(self,time_input):
        self.datetime=time_input
        self.price=self.hist_bar['close'][-1]
        self.close_price=self.hist_bar['close'][-1]
        self.high=self.hist_bar['high'][-1]
        self.low=self.hist_bar['low'][-1]
        self.volume=self.hist_bar['volume'][-1]
        self.open_price=self.hist_bar['open'][-1]
        self.hist_daily['high'][-1]=self.daily_high_price
        self.hist_daily['low'][-1]=self.daily_low_price
        self.hist_daily['close'][-1]=self.price
    
    def mavg(self, n):
        return pd.rolling_mean(self.hist_daily['close'],n)[-1]

    def returns(self):
        if self.hist['close'][-2]>0.000001:
            return (self.hist_daily['close'][-1]-self.hist_daily['close'][-2])/self.hist_daily['close'][-2]            
        else:
            return 0.0
    def stddev(self, n):
        return pd.rolling_std(self.hist_daily['close'],n)[-1]

    def vwap(self, n):
        return pd.rolling_sum(self.hist_daily['volume']*self.hist_daily['close'],n)/pd.rolling_sum(self.hist_daily['volume'],n)

class HistClass(object):
    def __init__(self, security=None, period='1 day'):
        self.status=None
        self.security=security
        self.period=period
        self.hist=pd.DataFrame(columns=['open','high','low','close','volume'])


class OrderClass(object):
    def __init__(self,orderId, created, parentOrderId = None, stop = None, 
                 limit = None, amount = 0, sid = None, filled = 0,
                 stop_reached = False, limit_reached = False, commission = None,
                 remaining = 0, status = 'na', contract = None, order = None, 
                 orderstate = None):
        self.orderId=orderId
        self.parentOrderId = parentOrderId
        self.created=created
        self.stop=stop
        self.limit=limit
        self.amount=amount
        self.sid=sid
        self.filled=filled
        self.stop_reached=stop_reached
        self.limit_reached=limit_reached
        self.commission=commission
        self.remaining=remaining
        self.status=status
        self.contract=contract
        self.order=order
        self.orderstate=orderstate

if __name__ == '__main__':
    stockList = pd.read_csv('all_US_Stocks.csv')
    print stockList.shape