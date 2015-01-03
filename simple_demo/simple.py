#!/usr/bin/env python

import IBCpp  # You need to link/copy IBCpp.so to the same directory 
import sys
import datetime, pytz


class MyClient(IBCpp.IBClient) :  #  define a new client class. All client classes are recommended to derive from IBClient unless you have special need.  
    def setup(self):
        self.state = "initial"
        self.stime = None
        self.stime_previous = None
        """ determine US Eastern time zone depending on EST or EDT """
        if datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EDT':
            self.USeasternTimeZone = pytz.timezone('Etc/GMT+4')
        elif datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EST':
            self.USeasternTimeZone = pytz.timezone('Etc/GMT+5')   
        else:
            self.USeasternTimeZone = None        
        
    def currentTime(self, tm):
        """
        IB C++ API call back function. Return system time in datetime instance
        constructed from Unix timestamp using the USeasternTimeZone from MarketManager
        """
        self.stime = datetime.datetime.fromtimestamp(float(str(tm)), 
                                                    tz = self.USeasternTimeZone)
                                                    
    def tickPrice(self, TickerId, tickType, price, canAutoExecute):
        '''
        This function will be called once price changes automatically
        '''
        print "TicketId='%d'" % TickerId
        print "TicketType='%d'" % tickType
        print "price='%f'" % price
        print "canAutoExecute='%d'" % canAutoExecute

    def runStrategy(self) :
        '''
        This should be your trading strategy's main entry. It will be called at the beginning of processMessages()
        '''
        if self.state == "initial":
            contract = IBCpp.Contract()
            contract.symbol = "TSLA"
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.primaryExchange = "NASDAQ"
            self.reqMktData(0, contract, '221', False)  # Once it called, market data will flow-in and corresponding events will be tricked automatically. 
            self.state = "datareqed" # change the state so that you won't request the same data again. 
        

        
if __name__ == '__main__' :
#    port = int(sys.argv[1])
#    if len(sys.argv[1:]) > 1 :
#        clientID = int(sys.argv[2])
#    else :
#        clientID = 0
    port = 7496; clientID = 1
    c = MyClient()  # create a client object
    c.setup();      # additional setup. It's optional.
    c.connect("", port, clientID) # you need to connect to the server before you do anything.
    c.reqCurrentTime()
    while(1):
        if (c.stime is not None and c.stime_previous is None):
            c.stime_previous = c.stime
            print "current system time: ", c.stime, datetime.datetime.now(tz = c.USeasternTimeZone)
        c.processMessages()       # put this function into infinit loop. A better way is to put it into a new thread. 
        
    
