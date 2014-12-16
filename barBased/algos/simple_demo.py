import datetime

def initialize(context):
    context.security = symbols('EUR.USD','AUD.USD')
    context.flag=1

def handle_data(context, data):
    print datetime.datetime.now()
    if context.flag==1:
        #order_target(symbol('XLB'),300)
        print history(20,'1d','price')
        context.flag=2        
    #for ct in context.portfolio.openOrderBook:
    #    print context.portfolio.openOrderBook[ct].__dict__
