import datetime

def initialize(context):
    context.security = symbols('AAPL', 'IBM')
    context.flag=1

def handle_data(context, data):
    if context.flag == 1:
        order_with_SL_TP(sec = symbol('AAPL'), amount = 10, 
                         stopLossPrice = 110.0, takeProfitPrice = 115.0)
        context.flag = 2
#    print datetime.datetime.now()
#    for sec in data:
#        print sec.symbol, data[sec].price
#    for ct in context.portfolio.openOrderBook:
#        print context.portfolio.openOrderBook[ct]
