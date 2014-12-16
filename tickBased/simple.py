#!/usr/bin/env python

import IBpy  # You need to link/copy IBpy.so to the same directory 
import sys


class MyClient(IBpy.IBClient) :  #  define a new client class. All client classes are recommended to derive from IBClient unless you have special need.  
    def setup(self):
        self.state = "initial"
        
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
            contract = IBpy.Contract()
            contract.symbol = "TSLA"
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.primaryExchange = "NASDAQ"
            self.reqMktData(888, contract, '221', False)  # Once it called, market data will flow-in and corresponding events will be tricked automatically. 
            self.state = "datareqed" # change the state so that you won't request the same data again. 
        

        
if __name__ == '__main__' :
    port = int(sys.argv[1])
    if len(sys.argv[1:]) > 1 :
        clientID = int(sys.argv[2])
    else :
        clientID = 0

    c = MyClient()  # create a client object
    c.setup();      # additional setup. It's optional.
    c.connect("", port, clientID) # you need to connect to the server before you do anything. 
    while(1):
        c.processMessages()       # put this function into infinit loop. A better way is to put it into a new thread. 
        
    
