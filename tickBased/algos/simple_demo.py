import datetime

def initialize(context):
    context.security = symbols('EUR.USD', 'GBP.USD')
    context.flag=1
    print 'i am in init'

def handle_data(context, data):
    print 'i am in handle_data'
    if context.flag == 1:
        for security in data:
            print security.symbol+'.'+security.currency
            print data[security].hist_daily
        #print history(20, '1d', 'close_price')
        context.flag = 2

#    if context.flag == 1:
#        order_with_SL_TP(sec = symbol('AAPL'), amount = 10, 
#                         stopLossPrice = 110.0, takeProfitPrice = 115.0)
#        context.flag = 2
#    print datetime.datetime.now()
#    for sec in data:
#        print sec.symbol, data[sec].price
#    for ct in context.portfolio.openOrderBook:
#        print context.portfolio.openOrderBook[ct]
