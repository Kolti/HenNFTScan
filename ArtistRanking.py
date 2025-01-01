# -*- coding: utf-8 -*-
"""
Created on Sun Sep 26 11:19:15 2021

@author: julia
"""

import requests
import json
import pandas as pd
from time import sleep
import smtplib
from email.mime.text import MIMEText
import numpy as np
import DateUtils
from MailUtils import SendMail

pd.options.mode.chained_assignment = None  # default='warn'
NoSaleDaysTolerance = 1
NoSaleHoursTolerance = 0
unit = 1000000

url = 'https://api.hicdex.com/v1/graphql'

def GetQuery(fromDate, toDate):
    query = """query{
          hic_et_nunc_trade(where: {timestamp: {_gt: \"""" + fromDate + """\", _lte: \"""" + toDate + """\"}}, order_by: {swap: {price: desc}}) {
      timestamp
      swap {
        price
        creator_id
      }
      token {
        title
        id
        supply
        royalties
        timestamp
        creator {
          name
        }
        creator_id
      }
    }
              }"""
    return query

def GetCombined(daysInInterval, numIntervals, startTime):
    print("Pulling artists in {} batch(es):".format(numIntervals))
    for i in range(numIntervals):
        print('Batch ', i + 1)
        query = GetQuery(DateUtils.GetPrior(startTime,(i + 1) * daysInInterval,0),DateUtils.GetPrior(startTime,i * daysInInterval,0))
        while True:
            try:
                r = requests.post(url, json={'query': query}, timeout=600)
                json_data = json.loads(r.text)
                df = pd.json_normalize(json_data["data"]["hic_et_nunc_trade"])
                break
            except BaseException as e:
                print(e)
                sleep(20)
        df['primary'] = np.where(df['token.creator_id']==df['swap.creator_id'],1,0)
        a = df.groupby(['token.creator_id', 'token.creator.name', 'primary', 'token.id', 'token.title'], as_index=False).agg(totalPrice = pd.NamedAgg('swap.price','sum'),trades=pd.NamedAgg('timestamp','count'), supply=pd.NamedAgg('token.supply','max'), mintTime=pd.NamedAgg('token.timestamp','max'), royalties=pd.NamedAgg('token.royalties','max'))
        if i == 0:
            b = a
        else:
            b = pd.concat([a,b], axis=0)
            b = b.groupby(['token.creator_id', 'token.creator.name', 'primary', 'token.id', 'token.title'], as_index=False).agg({'totalPrice':'sum', 'trades':'sum', 'supply':'max', 'mintTime':'max', 'royalties':'max'})
    b['totalPrice'] =  b['totalPrice']/unit
    b['avgPrice'] = b['totalPrice']/b['trades']
    b['tradesPerSupply'] = b['trades']/b['supply']

    secondary = b[b['primary']==0]
    primary = b[b['primary']==1]
    combined = primary.merge(secondary[['token.id','primary','trades','totalPrice','avgPrice','tradesPerSupply']], left_on = 'token.id', right_on = 'token.id', how='left')
    combined['secToPrim'] = combined['avgPrice_y']/combined['avgPrice_x']
    combined['totalValueSec'] = combined['supply'] * combined['avgPrice_y']
    combined = combined[['token.creator_id', 'token.creator.name', 'token.id', 'token.title', 'mintTime', 'supply', 'royalties', 'avgPrice_x', 'avgPrice_y', 'secToPrim', 'totalValueSec', 'trades_x', 'trades_y', 'tradesPerSupply_x', 'tradesPerSupply_y']]
    return combined

def GetArtists(daysInInterval, numIntervals, shift):
    startTime = DateUtils.GetNDaysPrior(shift)
    combined = GetCombined(daysInInterval, numIntervals, startTime)   
    print('Total number of tokens found: ', combined.shape[0])
    hasSecondary = combined[~combined['trades_y'].isna()]
    hasNoSecondary = combined[combined['trades_y'].isna() & (combined['mintTime'] <= DateUtils.GetPrior(startTime,NoSaleDaysTolerance,NoSaleHoursTolerance))]
    hasSecondary['markup'] = hasSecondary['avgPrice_y']-hasSecondary['avgPrice_x']
    hasSecondary = hasSecondary.groupby(['token.creator_id', 'token.creator.name'], as_index=False).agg(tokenCount=pd.NamedAgg('token.id','count'),avgSupply=pd.NamedAgg('supply','mean'),avgPricePrim=pd.NamedAgg('avgPrice_x','mean'),avgPriceSec=pd.NamedAgg('avgPrice_y','mean'),avgTradesPrim=pd.NamedAgg('trades_x','mean'),avgTradesSec=pd.NamedAgg('trades_y','mean'),minSecToPrim=pd.NamedAgg('secToPrim','min'),avgSecToPrim=pd.NamedAgg('secToPrim','mean'),maxSecToPrim=pd.NamedAgg('secToPrim','max'),avgTotalValueSec=pd.NamedAgg('totalValueSec','mean'),avgMarkup=pd.NamedAgg('markup','mean'))
    hasSecondary['avgSecToPrimAlt'] = hasSecondary['avgPriceSec']/hasSecondary['avgPricePrim']
    hasSecondary['tradesPerSupplyPrim'] = hasSecondary['avgTradesPrim']/hasSecondary['avgSupply']
    hasSecondary['tradesPerSupplySec'] = hasSecondary['avgTradesSec']/hasSecondary['avgSupply']
    hasNoSecondary = hasNoSecondary.groupby(['token.creator_id', 'token.creator.name'], as_index=False).agg(notSoldCount=pd.NamedAgg('token.id','count'))
        
    final = hasSecondary.merge(hasNoSecondary[['token.creator_id','notSoldCount']], on='token.creator_id', how = 'left')
    print('Total number of artists with secondary market sales found: ', final.shape[0])
    del hasSecondary, hasNoSecondary
    final['notSoldCount'] = final['notSoldCount'].fillna(0)
    final['noSaleRate'] = final['notSoldCount']/(final['tokenCount'] + final['notSoldCount'])
    latest = combined.sort_values('mintTime').groupby('token.creator_id').tail(1)
    final = final.merge(latest[['token.creator_id', 'mintTime', 'secToPrim','totalValueSec']], on = 'token.creator_id')
    del latest
    final.rename(columns={'secToPrim':'lastSecToPrim', 'mintTime':'lastMintTime','totalValueSec':'lastTotalValueSec'}, inplace=True)
    
    final = final[final['avgMarkup']>=10]
    final = final[(final['avgSupply']<=5) | (final['avgTradesSec']>=2)]
    final = final[(final['tokenCount']>=2) | (final['avgTradesSec']>=3)]
    final = final[final['noSaleRate']<=0.1]
    final = final[final['tradesPerSupplySec']>=0.2]
    final = final[final['avgSecToPrimAlt']>=2]
    final = final[(final['lastSecToPrim']>=1.75) | ((final['lastMintTime'] >= DateUtils.GetPrior(startTime,NoSaleDaysTolerance,NoSaleHoursTolerance)) & (final['minSecToPrim'] >=1.75) & final['lastSecToPrim'].isna())]
    
    combined = combined[combined['token.creator_id'].isin(final['token.creator_id'])].sort_values('mintTime', ascending=False)
    
    combined = combined.reset_index(drop=True)
    final = final.reset_index(drop = True)
    subject = "Artists Selected"
    body = final.to_html()
    SendMail(subject, body)
    print('Artists selected:')
    print(*final['token.creator.name'], sep='\n')
    print('Addresses:')
    print(*final['token.creator_id'], sep='\n')
    return(final, combined)

   