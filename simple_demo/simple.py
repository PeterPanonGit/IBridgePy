#!/usr/bin/env python

import IBCpp  # You need to link/copy IBCpp.so to the same directory 
import sys
import datetime, pytz, time
from IBridgePy.IBridgePyBasicLib.IBAccountManager import MSG_TABLE
import BasicPyLib.simpleLogger as simpleLogger

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
        self.log = simpleLogger.SimpleLoggerClass(filename = 'log.txt', 
                                                  logLevel = simpleLogger.NOTSET)
        
    def currentTime(self, tm):
        """
        IB C++ API call back function. Return system time in datetime instance
        constructed from Unix timestamp using the USeasternTimeZone from MarketManager
        """
        self.stime = datetime.datetime.fromtimestamp(float(str(tm)), 
                                                    tz = self.USeasternTimeZone)
                   
    def tickString(self, tickerId, field, value):
        """
        IB C++ API call back function. The value variable contains the last 
        trade price and volume information. User show define in this function
        how the last trade price and volume should be saved
        """
        # tickerId is indexed to data, so here we need to use data too
        valueSplit = value.split(';')
        if len(valueSplit) > 1 and float(valueSplit[1]) > 0:
            timePy = float(valueSplit[2])/1000
            priceLast = float(valueSplit[0]); sizeLast = float(valueSplit[1])
            currentTimeStamp = time.mktime(datetime.datetime.now().timetuple())
#            self.log.debug(__name__ + ', ' + str(tickerId) + ", " + str(sec.symbol)
#            + ', ' + str(priceLast)
#            + ", " + str(sizeLast) + ', ' + str(timePy) + ', ' + str(currentTime))
            # update price
            newRow = [timePy, priceLast, sizeLast, currentTimeStamp]
            print newRow
                                 
    def tickPrice(self, TickerId, tickType, price, canAutoExecute):
        '''
        This function will be called once price changes automatically
        '''
        self.log.debug(__name__ + ', ' + str(TickerId) + ", " + MSG_TABLE[tickType]
                + ", price = " + str(price))
        if (tickType in [1, 2, 4, 9]):
            print "TicketId='%d'" % TickerId
            print "TicketType='%d'" % tickType
            print "price='%f'" % price
            print "canAutoExecute='%d'" % canAutoExecute

        
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
    contract = IBCpp.Contract()
    contract.symbol = "IBM"
    contract.secType = "STK"
    contract.exchange = "SMART"
    contract.primaryExchange = "NYSE"
    c.reqMktData(1, contract, '233', False)  # Once it called, market data will flow-in and corresponding events will be tricked automatically.     
    while(1):
        if (c.stime is not None and c.stime_previous is None):
            c.stime_previous = c.stime
            print "current system time: ", c.stime, datetime.datetime.now(tz = c.USeasternTimeZone)
        c.runStrategy()
        c.processMessages()       # put this function into infinit loop. A better way is to put it into a new thread. 
        
    
