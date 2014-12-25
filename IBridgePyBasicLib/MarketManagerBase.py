# -*- coding: utf-8 -*-
"""
Module MarketManager

"""
import time, datetime, pytz
import logging
import os

from BasicPyLib.FiniteState import FiniteStateClass

class __USEasternMarketObject__(object):
    """
    MarketObject is the abstract base class which manages algorithmic trading algorithms
    When initializes it will determine the US Eastern time time zone
    The basic method is run_according_to_market(), which sleeps when market closes
    and runs when market is open from 9:30am to 4pm EST
    inherited classes should overwrite init_obj(), run_client_algorithm() and destroy_obj()
    """
    def __init__(self, PROGRAM_DEBUG = False, MARKET_DEBUG = True):
        """ determine US Eastern time zone depending on EST or EDT """
        if datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EDT':
            self.USeasternTimeZone = pytz.timezone('Etc/GMT+4')
        elif datetime.datetime.now(pytz.timezone('US/Eastern')).tzname() == 'EST':
            self.USeasternTimeZone = pytz.timezone('Etc/GMT+5')   
        else:
            self.USeasternTimeZone = None
            
        # state of market
        class USEasternMarketStateClass(FiniteStateClass):
            def __init__(self):
                self.SLEEP = 'SLEEP'; self.RUN = 'RUN'
        self.marketState = USEasternMarketStateClass()
        self.marketState.set_state(self.marketState.SLEEP)
        
        # DEBUG levels
        self.PROGRAM_DEBUG = PROGRAM_DEBUG
        self.MARKET_DEBUG = MARKET_DEBUG
        
    def init_obj(self):
        pass
    
    def run_client_algorithm(self):
        pass
    
    def destroy_obj(self):
        pass
    
    def run_according_to_market(self, market_start_time = '9:30:00', 
                                market_close_time = '16:00:00'):
        """
        run_according_to_market() will check if market is open every one second
        if market opens, it will first initialize the object and then run the object
        if market closes, it will turn the marketState back to "sleep"
        """
        while (self.marketState.is_state(self.marketState.SLEEP)):
            time.sleep(1) # check if market is open every one second
            currentTime = datetime.datetime.now(self.USeasternTimeZone)
            dataDate = str(currentTime).split(' ')[0]
            startTime = datetime.datetime.strptime(dataDate + ' ' + market_start_time , '%Y-%m-%d %H:%M:%S')
            startTime = startTime.replace(tzinfo = self.USeasternTimeZone)
            endTime = datetime.datetime.strptime(dataDate + ' ' + market_close_time, '%Y-%m-%d %H:%M:%S')
            endTime = endTime.replace(tzinfo = self.USeasternTimeZone)           
    #        print currentTime.hour, currentTime.minute, currentTime.second
            if (self.marketState.is_state(self.marketState.SLEEP) \
            and (currentTime > startTime) and (currentTime < endTime) \
            and currentTime.isoweekday() in range(1, 6)):
                self.marketState.set_state(self.marketState.RUN)
                print 'start to run at: ', currentTime
                self.init_obj()
            while (self.marketState.is_state(self.marketState.RUN)):
                self.run_client_algorithm()
                currentTime = datetime.datetime.now(self.USeasternTimeZone)
                if (currentTime >= endTime):
                    print "Market is closed at: ", currentTime
                    self.destroy_obj()
                    self.marketState.set_state(self.marketState.SLEEP) 
                    
class MarketManager(__USEasternMarketObject__):
    """ 
    Market Manager will run trading strategies according to the market hours.
    It should contain a instance of IB's client, properly initialize the connection
    to IB when market starts, and properly close the connection when market closes
    inherited from __USEasternMarketObject__. 
    USeasternTimeZone and run_according_to_market() are inherited
    init_obj(), run_algorithm() and destroy_obj() should be overwritten
    """    
    def __init__(self, PROGRAM_DEBUG = False, MARKET_DEBUG = True, 
                 port = 7496, clientID = 1, trader = None):
        """
        initializtion: create log file and IBClient
        a trader instance must be passed in which has already run setup()
        """
        super(MarketManager, self).__init__(PROGRAM_DEBUG = PROGRAM_DEBUG, 
            MARKET_DEBUG = MARKET_DEBUG)
        
        # define the trade type
        if (trader is not None):
            self.IBClient = trader
        else:
            raise ValueError("trader can't be None. Must be an initiated instance!")
            
        # sync timezone
        self.IBClient.USeasternTimeZone = self.USeasternTimeZone
        self.IBClient.log.info(__name__ + ": " + "accountCode: " + 
        str(self.IBClient.accountCode))
            
    ######### this part do real trading with IB
    def init_obj(self):
        """
        initialzation of the connection to IB
        updated account
        """
        logger = logging.getLogger('TraderLog')
        logger.setLevel(logging.NOTSET)
        # create a file handler
        self.todayDateStr = time.strftime("%Y-%m-%d")
        if not os.path.exists('Log'):
            os.makedirs('Log')
        file_handler = logging.FileHandler('Log/TraderLog_' + self.todayDateStr + '.txt', mode = 'w')
        file_handler.setLevel(logging.NOTSET)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.NOTSET)
        # create a logging format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        # add the handlers to the logger
        logger.addHandler(file_handler)        
        # trader log for everyday trading log
        self.IBClient.log = logger
        
        # connect to IB server, TWS is the default
        self.IBClient.connect("", self.IBClient.port, self.IBClient.clientId) # connect to server
        self.IBClient.log.info(__name__ + ": " + "Connected to IB, port = " + 
        str(self.IBClient.port) + ", ClientID = " + str(self.IBClient.clientId))
            
    def run_client_algorithm(self):
        '''
        This should be your trading strategy's main entry. 
        It will be called at the beginning of processMessages()
        '''
#        if (self.IBClient.PROGRAM_DEBUG):
#            print self.IBClient.traderState, self.IBClient.accountManagerState
        self.IBClient.runAlgorithm()
        self.IBClient.processMessages()
    
    def destroy_obj(self):
        """
        disconnect from IB and close log file
        """
        self.IBClient.disconnect()
        handlers = self.IBClient.log.handlers[:]
        for handler in handlers:
            handler.close()
            self.IBClient.log.removeHandler(handler)