import pandas as pd
import time
from time import sleep
from pytz import timezone
import yaml
import json
import datetime as dt
import numpy as np
import pyotp
def Straddle():
 

    global master_contract, api, Log, TradeCount
    Log = {}
    path ='./'
    from ShoonyaApipy import api_helper

    #API object 
    api = api_helper.ShoonyaApiPy()

    #Read Cred
    with open('cred.yml') as f:
        cred = yaml.load(f, Loader=yaml.FullLoader)
        print(cred)

    #Login
    totp = pyotp.TOTP(cred['factor2']).now()
    ret = api.login(userid=cred['user'], password=cred['pwd'],
                    twoFA=totp, vendor_code=cred['vc'], api_secret=cred['apikey'], imei=cred['imei'])
    master_contract = pd.read_csv('https://shoonya.finvasia.com/NFO_symbols.txt.zip',compression='zip',engine='python',delimiter=',')
    master_contract['Expiry'] = pd.to_datetime(master_contract['Expiry'])
    master_contract['StrikePrice'] =master_contract['StrikePrice'].astype(float)
    master_contract.sort_values('Expiry',inplace=True)
    master_contract.reset_index(drop=True,inplace=True)

    def get_instrument(Symbol,strike_price,optiontype,expiry_offset):
        #To get a instrument token from the master contract downloaded from shoonya website
        return(master_contract[(master_contract['Symbol']==Symbol) & (master_contract['OptionType']==optiontype) &
                            (master_contract['StrikePrice']==strike_price)].iloc[expiry_offset])

    def get_atm_strike(Symbol):
        if Symbol == 'BANKNIFTY':
            base = 100
        elif Symbol == 'NIFTY':
            base = 50
        bnspot_token = api.searchscrip(exchange='NSE',searchtext=Symbol)['values'][0]['token']
        while True:
            bnflp = float(api.get_quotes(exchange='NSE',token=bnspot_token)['lp'])
            if bnflp != None :
                break
        atmprice = round(bnflp/base)*base
        return atmprice

    def place_order(BS, tradingsymbol, quantity, product_type='I', price_type='MKT', exchange='NFO', price=0, trigger_price=None):
        order_place = api.place_order(buy_or_sell=BS, product_type=product_type, exchange=exchange, tradingsymbol=tradingsymbol,
                                    quantity=quantity, discloseqty=0, price_type=price_type,
                                    price=price, trigger_price=trigger_price) #M for NRML and I for intradayin product type
        return order_place['norenordno']

    def stop_loss_order(Qty, tradingsymbol, price, SL):
        stop_price = price+SL
        price = stop_price+2
        trigger_price = stop_price
        stop_loss_orderid = place_order(BS='B', tradingsymbol=tradingsymbol, quantity=Qty, price_type='SL-LMT',price=price, trigger_price=trigger_price)
        return stop_loss_orderid

    def single_order_history(orderid,req) :
        #This required to made to avoid unnecessory making a lot of Dataframes
        dl=pd.DataFrame(api.single_order_history(orderid))
        return dl[req].iloc[0]
        while True :
            json_data=api.single_order_history(orderid)
            if json_data!= None :
                break
        for id in json_data:
            value_return=id[req]
            break
        return value_return


    def Trade(Parameter,TradeCount):

        #Getting ATM Strike
        atm_strike=get_atm_strike(Parameter['Symbol'])
        print(atm_strike)

        #Getting Symbols
        ce_tradingsymbol=get_instrument(Parameter['Symbol'],atm_strike,'CE',0)['TradingSymbol']
        pe_tradingsymbol=get_instrument(Parameter['Symbol'],atm_strike,'PE',0)['TradingSymbol']


        #Place Order
        ce_orderid=place_order('S',ce_tradingsymbol,Parameter['Qty'])
        pe_orderid=place_order('S',pe_tradingsymbol,Parameter['Qty'])
        
        sleep(1)

        # ce_price=single_order_history(ce_orderid,'avgprc')
        # pe_price=single_order_history(pe_orderid,'avgprc')
        ce_price = 500
        pe_price = 500

        #Stoploss Order
        ce_slorderid =stop_loss_order(Parameter['Qty'],ce_tradingsymbol,ce_price,Parameter['StopLossPoint'])
        pe_slorderid =stop_loss_order(Parameter['Qty'],pe_tradingsymbol,pe_price,Parameter['StopLossPoint'])

        Log[TradeCount] = {'ce_tradingsymbol':ce_tradingsymbol,'pe_tradingsymbol':pe_tradingsymbol,
                        'ce_orderid':ce_orderid,'pe_orderid':pe_orderid,'ce_slorderid':ce_slorderid,'pe_slorderid':pe_slorderid,'ce_price':ce_price,'pe_price':pe_price}

        return Log

    with open(f'{path}/INFO/Strategy.json','r') as f:
        Parameter = json.load(f)
    
    Entry = Parameter['EntryTime'].split(',')
    Entry = [int(i) for i in Entry]

    Exit = Parameter['ExitTime'].split(',')
    Exit = [int(i) for i in Exit]
    
    TradeCount = 0

    #First order
    while dt.datetime.now(timezone("Asia/Kolkata")).time() < dt.time(Entry[0],Entry[1],Entry[2]):
        sleep(1)
    


    Trade(Parameter,TradeCount)
        
    while TradeCount < Parameter['MaxRetry']+1:

        #Exit ALL Scrip
        try:
            with open(f'{path}/INFO/Algostatus.json','r') as f:
                Algostatus= json.load(f)
        except:
            time.sleep(1)
            with open(f'{path}/INFO/Algostatus.json','r') as f:
                Algostatus= json.load(f)

        print(Algostatus)
        if Algostatus['status'] =='Active':
            
        
            
            #-----RENTRY-----
            print("TradeCount----",TradeCount)
            ce_sl_status = single_order_history(Log[TradeCount]['ce_slorderid'], 'status')
            pe_sl_status = single_order_history(Log[TradeCount]['pe_slorderid'], 'status')
            if pe_sl_status == 'COMPLETE' and ce_sl_status =='COMPLETE':
                TradeCount+=1
                Trade(Parameter,TradeCount)

            #----EXIT TIME----
            if dt.datetime.now(timezone("Asia/Kolkata")).time() > dt.time(Exit[0],Exit[1],Exit[2]):
                ce_sl_status = single_order_history(Log[TradeCount]['ce_slorderid'], 'status')
                pe_sl_status = single_order_history(Log[TradeCount]['pe_slorderid'], 'status')
                with open(f'./Logs/{dt.date.today()}.json','w') as f:
                    json.dump(Log,f)
                if ce_sl_status=='TRIGGER_PENDING' and pe_sl_status== 'COMPLETE':
                    api.cancel_order(Log[TradeCount]['ce_slorderid'])
                    place_order('B',Log[TradeCount]['ce_tradingsymbol'],Parameter['Qty'])
                    break
                if pe_sl_status == 'TRIGGER_PENDING' and ce_sl_status == 'COMPLETE':
                    api.cancel_order(Log[TradeCount]['pe_slorderid'])
                    place_order('B',Log[TradeCount]['pe_tradingsymbol'],Parameter['Qty'])
                    break
                if pe_sl_status == 'TRIGGER_PENDING' and ce_sl_status == 'TRIGGER_PENDING':
                    api.cancel_order(Log[TradeCount]['ce_slorderid'])
                    place_order('B', Log[TradeCount]['ce_tradingsymbol'], Parameter['Qty'])
                    api.cancel_order(Log[TradeCount]['pe_slorderid'])
                    place_order('B', Log[TradeCount]['pe_tradingsymbol'], Parameter['Qty'])
                    break
        else:
            try:
                ce_sl_status = single_order_history(Log[TradeCount]['ce_slorderid'], 'status')
                pe_sl_status = single_order_history(Log[TradeCount]['pe_slorderid'], 'status')
                print(ce_sl_status,pe_sl_status)
                with open(f'./Logs/{dt.date.today()}.json','w') as f:
                    json.dump(Log,f)
                if ce_sl_status=='TRIGGER_PENDING' and pe_sl_status== 'COMPLETE':
                    api.cancel_order(Log[TradeCount]['ce_slorderid'])
                    place_order('B',Log[TradeCount]['ce_tradingsymbol'],Parameter['Qty'])
                    break
                if pe_sl_status == 'TRIGGER_PENDING' and ce_sl_status == 'COMPLETE':
                    api.cancel_order(Log[TradeCount]['pe_slorderid'])
                    place_order('B',Log[TradeCount]['pe_tradingsymbol'],Parameter['Qty'])
                    break
                if pe_sl_status == 'TRIGGER_PENDING' and ce_sl_status == 'TRIGGER_PENDING':
                    api.cancel_order(Log[TradeCount]['ce_slorderid'])
                    place_order('B', Log[TradeCount]['ce_tradingsymbol'], Parameter['Qty'])
                    api.cancel_order(Log[TradeCount]['pe_slorderid'])
                    place_order('B', Log[TradeCount]['pe_tradingsymbol'], Parameter['Qty'])
                    break
                break
            except Exception as e:
                print("Algo is OFF today or encounter an error",e)

            
     
if __name__ == '__main__':
    while True:
        import glob
        Latest = sorted(glob.glob('./Logs/*'))[-1]
        Latest = Latest.split('.')[1].split('/')[-1]
        Date = dt.datetime.strptime(Latest,'%Y-%m-%d').date()
        if  Date ==dt.date.today():
            try:
                with open(f'./INFO/Algostatus.json','r') as f:
                    Algostatus= json.load(f)
            except:
                time.sleep(1)
                with open(f'./INFO/Algostatus.json','r') as f:
                    Algostatus= json.load(f)
            if Algostatus['status'] =='Active':
                print("Algo Started")

                Straddle()