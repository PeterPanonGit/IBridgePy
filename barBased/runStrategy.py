# -*- coding: utf-8 -*-

# There is only one account linked to the login, because reqAccountUpdate(True, 'All')
# Assume there is not pending orders, because self.order_target_quantopin does not handle pending orders



# import all Quantopian compatable functions here
from quantopian import symbol, symbols, LimitOrder,StopOrder,MarketOrder,StopLimitOrder
import pandas as pd

#####################################################################################
from class_IBtrading import IBtrading                                      
import time
import datetime
from quantopian import DataClass

# import strategy here. Only one strategy can be imported

class IBtrading(IBtrading):

    def init_setup(self):
        '''
        pass the context object to intialize() for initialization
        '''
        initialize(self.context)

        try:        
            if len(self.context.security)>=2:
                for ct in self.context.security:
                    self.data[ct]=DataClass()
        except:
            self.data[self.context.security]=DataClass()
        self.state='init'     
        self.machine_state='first_step'
        self.reqCurrentTime()
        self.reqPositions()
        self.context.portfolio.start_date=datetime.datetime.now()
        
    def runStrategy(self) :
        '''
        This should be your trading strategy's main entry. 
        It will be called at the beginning of processMessages()
        '''

        self.reqCurrentTime()
        
        if self.state=='init':
            if self.machine_state=='first_step':
                self.req_hist_price(endtime=datetime.datetime.now())
                self.re_send=0
                self.req_real_time_price()
                self.reqAccountUpdates(True,'All')
                self.set_timer()
                self.machine_state='second_step'
            if self.machine_state=='second_step': 
                self.check_timer('second_step')
                cmpt=True
                if self.req_hist_price_check_end() !=True: 
                    cmpt=False
                    #self.display('hist not ready')
                #if self.req_real_time_price_check_end() != True:
                #    cmpt=False
                #    print 'real time price is not ready'
                if cmpt==True:
                    for security in self.returned_hist:
                        self.data[security].hist_daily=self.returned_hist[security].hist
                    self.state='main'
                    self.machine_state='sleep'
                    print 'EA start'
                    self.display_account_info()


        if self.state=='main':
            # At the beginning of every minute, request hist_minute_price
            # Every day, at 14:15 EST, request hist_daily_price
            if self.stime.second==0 and self.stime_previous.second!=0:
                if self.stime.hour==14 and self.stime.minute==15 and self.state.second==0 :
                    self.machine_state='req_daily_price_first'
                else:
                    self.machine_state='req_minute_price_first'
                
            # Request hist_daily    
            if self.machine_state=='req_daily_price_first':
                self.req_hist_price(endtime=datetime.datetime.now())
                self.machine_state='req_daily_price_second' 
                self.set_timer()
            if self.machine_state=='req_daily_price_second':
                self.check_timer('req_minute_price_second',2)
                if self.req_hist_price_check_end():
                    for security in self.returned_hist:
                        self.data[security].hist_daily=self.returned_hist[security].hist                      
                    self.machine_state='req_minute_price_first'

            # Request hist_minute    
            if self.machine_state=='req_minute_price_first':
                self.req_hist_price(endtime=datetime.datetime.now(), goback='6000', barSize='1 min')
                self.machine_state='req_minute_price_second' 
                self.set_timer()
            if self.machine_state=='req_minute_price_second':
                self.check_timer('req_minute_price_second',2)
                if self.req_hist_price_check_end():
                    for security in self.returned_hist:
                        self.data[security].hist_minute=self.returned_hist[security].hist                      
                    self.machine_state='update_portfolio_first'

            # Update portfolio        
            if self.machine_state=='update_portfolio_first':
                self.reqAccountUpdates(True,'All') 
                self.accountDownloadEndstatus='Submitted'
                self.machine_state='update_portfolio_second' 
                self.set_timer()
            if self.machine_state=='update_portfolio_second':
                self.check_timer('update_portfolio_second',2)
                if self.accountDownloadEndstatus=='Done':
                    self.machine_state='evey_minute_run'
                    
            if self.machine_state=='evey_minute_run':        
                # Update self.data using recent minute data
                for security in self.data:                        
                    self.data[security].update(self.stime)                     

                # Update the last_sale_price of holding positions
                for security in self.context.portfolio.positions: 
                    self.context.portfolio.positions[security].last_sale_price=self.data[security].price

                # Run handle_data
                handle_data(self.context, self.data)

                # Set machine_state to 'sleep' and reset the counter of re_send
                self.machine_state='sleep'
                self.re_send=0

        self.stime_previous=self.stime                            
                        

if __name__ == '__main__' :
    import IBridgePy        
    port = 7496
    clientID = 0

    c = IBtrading()  # create a client object
    c.setup()
    c.logFileName = "log.txt"
    c.logOn()
    c.echo = True
    c.addMessageLevel(IBridgePy.MsgLevel.SYSERR)
    c.addMessageLevel(IBridgePy.MsgLevel.IBINFO)
    print "message level: ", "{0:b}".format(c.getMessageLevel())
    c.connect("", port, clientID) # you need to connect to the server before you do anything. 
    print "Connected!"
    ##### API methods
    order=c.order_quantopian
    order_value=c.order_value_quantopian
    order_percent=c.order_percent_quantopian
    order_target=c.order_target_quantopian
    order_target_value=c.order_target_value_quantopian
    order_target_percent=c.order_target_percent_quantopian
    cancel_order=c.cancel_order_quantopian
    get_open_order=c.get_open_order_quantopian
    get_datetime=c.get_datetime_quantopian
    history=c.history_quantopian
    #######
    
    ###### read in the algorithm script
    settings = pd.read_csv('settings.csv')
    print "Now running algorithm: ", settings['Algorithm'][0]
    with open('algos/' + settings['Algorithm'][0] + '.py') as f:
        script = f.read()
    print script
    exec(script)
    ######
    
    c.init_setup()

    while(1):
        time.sleep(0.1)
        c.processMessages()       # put this function into infinit loop. A better way is to put it into a new thread. 
        
         
        
    
