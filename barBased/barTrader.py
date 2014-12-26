#import IBCpp  # IBCpp.pyd is the Python wrapper to IB C++ API
import datetime
import time

from IBridgePy.IBridgePyBasicLib.quantopian import Security, ContextClass, \
PositionClass, HistClass, create_contract, MarketOrder,create_order, \
OrderClass, same_security, DataClass, symbol, symbols
from IBridgePy.IBridgePyBasicLib.IBAccountManager import IBAccountManager
from IBridgePy.IBridgePyBasicLib.MarketManagerBase import MarketManager
from BasicPyLib.FiniteState import FiniteStateClass

class BarTrader(IBAccountManager) :  #  define a new client class. All client classes are recommended to derive from IBClient unless you have special need.  
    """
    BarTraders are IBAccountManager too, so BarTraders inherits from IBAccountManager.
    Besides managing the account, BarTraders also make trade decisions for every
    unit time bar, such as 1 minute
    """
    def setup(self, PROGRAM_DEBUG = False, TRADE_DEBUG = True, port = 7496, clientId = 1,
              USeasternTimeZone = None, accountCode = 'ALL', minTick = 0.01, 
              barSize = datetime.timedelta(seconds = 60)):
        '''
        initialize BarTrader. First initialize the parent class IBAccountManager,
        then define the data structure for saving security data. 
        '''
        # call parent class's setup
        super(BarTrader, self).setup(PROGRAM_DEBUG = PROGRAM_DEBUG, 
            TRADE_DEBUG = TRADE_DEBUG, USeasternTimeZone = USeasternTimeZone, 
            accountCode = accountCode, minTick = minTick, port = port, clientId = clientId) 
        
        # barSize for BarTrader
        self.barSize = barSize
            
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
        
        if (self.PROGRAM_DEBUG):
            print("accountCode: ", self.accountCode)

    def API_initialize(self):
        # call Quantopian-like user API function
        initialize(self.context)
        # data is used to save the current security price info        
        self.data={}; 
        try:        
            if len(self.context.security)>=2:
                for ct in self.context.security:
                    self.data[ct] = DataClass()
        except:
            self.data[self.context.security] = DataClass()
        
    ############# trader specific order functions ###################
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
        
    def runAlgorithm(self):
        time.sleep(0.1) # sleep for sometime to avoid sending messages too fast
        self.reqCurrentTime()
        # initialize
        if self.traderState.is_state(self.traderState.INIT):
            if self.accountManagerState.is_state(self.accountManagerState.INIT):
                self.req_hist_price(endtime=datetime.datetime.now())
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
                    
        # main: every bar
        if self.traderState.is_state(self.traderState.TRADE):
            # At the beginning of every bar, request hist_bar_price
            # Every day, at 14:15 EST, request hist_daily_price
            # this is run regardless of accountManagerState
            if ((self.stime_previous is None and 
            self.accountManagerState.is_state(self.accountManagerState.WAIT_FOR_INIT_CALLBACK))
            or (self.stime_previous is not None and 
            self.stime - self.stime_previous > self.barSize)):
                self.stime_previous = self.stime
                if self.stime.hour == 14 and self.stime.minute == 15 and \
                self.state.second == 0 :
                    self.accountManagerState.set_state(
                    self.accountManagerState.REQ_DAILY_PRICE)
                else:
                    self.accountManagerState.set_state(
                    self.accountManagerState.REQ_BAR_PRICE)
                
            # Request hist_daily    
            if self.accountManagerState.is_state(self.accountManagerState.REQ_DAILY_PRICE):
#                print "request daily data"
                self.req_hist_price(endtime=datetime.datetime.now())
                self.accountManagerState.set_state(
                    self.accountManagerState.WAIT_FOR_DAILY_PRICE_CALLBACK)
                self.set_timer()
            if self.accountManagerState.is_state(
            self.accountManagerState.WAIT_FOR_DAILY_PRICE_CALLBACK):
                self.check_timer(self.accountManagerState.WAIT_FOR_DAILY_PRICE_CALLBACK, 2)
                if self.req_hist_price_check_end():
                    for security in self.returned_hist:
                        self.data[security].hist_daily = self.returned_hist[security].hist                      
                    self.accountManagerState.set_state(
                    self.accountManagerState.REQ_BAR_PRICE)
                    
            # Request hist_bar    
#            if (self.PROGRAM_DEBUG):
#                print self.accountManagerState
            if self.accountManagerState.is_state(
            self.accountManagerState.REQ_BAR_PRICE):
                self.req_hist_price(endtime=datetime.datetime.now(), 
                                    goback='6000', barSize='1 min')
                self.accountManagerState.set_state(
                self.accountManagerState.WAIT_FOR_BAR_PRICE_CALLBACK) 
                self.set_timer()
            if self.accountManagerState.is_state(
            self.accountManagerState.WAIT_FOR_BAR_PRICE_CALLBACK):
                self.check_timer(self.accountManagerState.WAIT_FOR_BAR_PRICE_CALLBACK, 10)
                if self.req_hist_price_check_end():
                    # save historical data to self.data
                    for security in self.returned_hist:
                        self.data[security].hist_bar = self.returned_hist[security].hist
                    self.accountManagerState.set_state(
                    self.accountManagerState.UPDATE_PORTFOLIO)

            # Update portfolio        
            if self.accountManagerState.is_state(
            self.accountManagerState.UPDATE_PORTFOLIO):
                self.reqAccountUpdates(True, self.accountCode) 
                self.accountDownloadEndstatus='Submitted'
                self.accountManagerState.set_state(
                self.accountManagerState.WAIT_FOR_UPDATE_PORTFOLIO_CALLBACK)
                self.set_timer()
            if self.accountManagerState.is_state(
            self.accountManagerState.WAIT_FOR_UPDATE_PORTFOLIO_CALLBACK):
                self.check_timer(self.accountManagerState.WAIT_FOR_UPDATE_PORTFOLIO_CALLBACK, 2)
                if self.accountDownloadEndstatus=='Done':
                    self.accountManagerState.set_state(
                    self.accountManagerState.EVERY_BAR_RUN)
#                    self.display_account_info()
                    
            if self.accountManagerState.is_state(self.accountManagerState.EVERY_BAR_RUN):   
                # Update self.data using recent bar data
                for security in self.data:                        
                    self.data[security].update(self.stime)                     

                # Update the last_sale_price of holding positions
                for security in self.context.portfolio.positions: 
                    self.context.portfolio.positions[security].last_sale_price = \
                    self.data[security].price

                # Run handle_data
                handle_data(self.context, self.data)

                # reset the counter of re_send and update stime_previous
                self.accountManagerState.set_state(self.accountManagerState.SLEEP)
                self.re_send = 0
            
if __name__ == '__main__' :
    import pandas as pd
    settings = pd.read_csv('settings.csv')
    
    trader = BarTrader()
    ##### API methods
    order = trader.order_quantopian
    order_value = trader.order_value_quantopian
    order_percent = trader.order_percent_quantopian
    order_target = trader.order_target_quantopian
    order_target_value = trader.order_target_value_quantopian
    order_target_percent = trader.order_target_percent_quantopian
    cancel_order = trader.cancel_order_quantopian
    get_open_order = trader.get_open_order_quantopian
    get_datetime = trader.get_datetime_quantopian
    history = trader.history_quantopian
    #######
    
    ###### read in the algorithm script

    print "Now running algorithm: ", settings['Algorithm'][0]
    with open('algos/' + settings['Algorithm'][0] + '.py') as f:
        script = f.read()
#    print script
    exec(script)
    ######
    
    trader.setup(PROGRAM_DEBUG = True, accountCode = settings['AccountCode'][0],
        barSize = datetime.timedelta(seconds = 
        int(settings['BarSize (in seconds)'][0])))
        
    c = MarketManager(PROGRAM_DEBUG = True, trader = trader)
    c.run_according_to_market(market_close_time = '23:59:00')
    
    print("Finished!")