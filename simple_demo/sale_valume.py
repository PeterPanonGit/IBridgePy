####################### INPUT here ##############################

# How often do you want to show the message?
how_often=60 # in seconds

# how long do you want to look back?
look_back=[60, 300, 600] # 1 min, 5 mintues, and 10 minutes

#################################################################

import IBCpp
import pandas as pd  
import datetime
import pytz

def create_contract(security):
    if security.split('.')[0]=='FUT':
        contract = IBCpp.Contract()
        contract.symbol = security.split('.')[1]
        contract.secType = 'FUT'
        contract.exchange = 'GLOBEX'
        contract.currency = security.split('.')[2]
        contract.expiry= security.split('.')[3]
        contract.primaryExchange='GLOBEX'
    if security.split('.')[0]=='CASH':
        contract = IBCpp.Contract()
        contract.symbol = security.split('.')[1]
        contract.secType = 'CASH'
        contract.exchange = 'IDEALPRO'
        contract.currency = security.split('.')[2]
        contract.primaryExchange='IDEALPRO'
    return contract 

def show_results(sales_record, x):
    current=datetime.datetime.now()
    #print sales_record
    past_1min=sales_record[sales_record.index>current-datetime.timedelta(seconds=x)]   
    sales_buy=past_1min[past_1min['type']=='BUY']['volume'].sum()
    print 'BUY volume in past %s seconds' %(x,),sales_buy               
    sales_sell=past_1min[past_1min['type']=='SELL']['volume'].sum()
    print 'SELL volume in past %s seconds' %(x,),sales_sell               
    sales_between=past_1min[past_1min['type']=='BETWEEN']['volume'].sum()
    print 'BETWEEN volume in past %s seconds' %(x,),sales_between               
    

class IBtrading(IBCpp.IBClient):
    
    def setup(self):
        print 'setup'
        self.machine_state='first'
        self.bid=0.0
        self.ask=0.0
        self.sales_record=pd.DataFrame()
        self.showtime_last=None
        self.stime=None

    def tickPrice(self, TickerId, tickType, price, canAutoExecute):
        #print TickerId, tickType, price, canAutoExecute
        if str(tickType)=='BID':
            self.bid=price
            print 'new bid',price
        if str(tickType)=='ASK':
            self.ask=price
            print 'new ask',price            

    def tickString(self, TickerId, tickType, value):
        #print TickerId, tickType, value
        if str(tickType)=='RT_VOLUME':
            #print 'RT_Volume'
            last_price,last_size,last_time,total_volume,vwap,single_trade=value.split(';')
            if float(last_price)<=self.bid:
                newRow=pd.DataFrame({'type':'SELL','volume':int(last_size)}, index=[datetime.datetime.now()])
                self.sales_record=self.sales_record.append(newRow)
            elif float(last_price)>=self.ask:
                newRow=pd.DataFrame({'type':'BUY','volume':int(last_size)}, index=[datetime.datetime.now()])
                self.sales_record=self.sales_record.append(newRow)
            else:
                newRow=pd.DataFrame({'type':'BETWEEN','volume':int(last_size)}, index=[datetime.datetime.now()])
                self.sales_record=self.sales_record.append(newRow)
 
    def runStrategy(self) :
        if self.machine_state=='first':
            self.reqMktData(0,create_contract('FUT.ES.USD.201503'),'233',False)
#            self.reqMktData(self.my_next_valid_id,create_contract('CASH.EUR.USD'),'233',False)
            self.showtime_last=datetime.datetime.now()            
            self.machine_state='second'
        elif self.machine_state=='second':
            current=datetime.datetime.now()
            self.reqCurrentTime()
            print self.stime            
            if current-self.showtime_last>datetime.timedelta(seconds=how_often):
                for ct in look_back:
                    show_results(self.sales_record,ct)
                self.showtime_last=current
                        
    def error(self, errorId, errorCode, errorString):
        print 'ERROR', errorId, errorCode, errorString

    def currentTime(self, tm):
        #self.stime=tm
        self.stime = datetime.datetime.fromtimestamp(float(str(tm)), tz = pytz.timezone('UTC'))
        
if __name__ == '__main__' :

    #import IBCpp
    import time        
    port = 7496
    clientID = 0

    c = IBtrading()  
    c.connect("", port, clientID)  
    c.setup()
    
    while(1):
        time.sleep(1)
        c.runStrategy()
        c.processMessages()       
         
        
    
