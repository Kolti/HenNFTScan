import requests
import json
import pandas as pd
from time import sleep
import datetime as dt
import ArtistRanking as ar
import DateUtils
from MailUtils import SendMail

url = 'https://api.hicdex.com/v1/graphql'
unit = 1000000
scanInterval = 6
errorInterval = 60
mailInterval = 5
daysInInterval = 3
numIntervals = 30
shift=0
maxPrice = 40
   
def SendNewListingMail(newTokenInfo, averageStats, tokenStats):
    supply = newTokenInfo['token.supply']
    royalties = round(newTokenInfo['token.royalties']/10)
    price = round(newTokenInfo["price"]/unit,1)
    avgPredPriceSec = round(averageStats['avgTotalValueSec'].iloc[0]/supply,1)
    lastPredPriceSec = round(averageStats['lastTotalValueSec'].iloc[0]/supply,1)
    avgPredValue = round(avgPredPriceSec*(1-royalties/100),1)
    lastPredValue = round(lastPredPriceSec*(1-royalties/100),1)
    subject = newTokenInfo["token.title"] + ". P/A/L: " + str(price)+ "/" + str(avgPredValue) + "/" + str(lastPredValue) + "."
    body = ("https://www.hicetnunc.xyz/objkt/" + str(newTokenInfo["token.id"]) + 
            "<br><br> Description: " + newTokenInfo["token.description"] +
            "<br> Artist: " + newTokenInfo["token.creator.name"] +
            "<br> Royalties: " + str(royalties) + "%"
            "<br> Editions: " + str(newTokenInfo['amount']) + "/" + str(supply) + 
            "<br> Price/pred avg/pred last: " + str(price) + "/" + str(avgPredPriceSec) + "/" + str(lastPredPriceSec) + 
            "<br>" + averageStats.to_html() + 
            "<br>" + tokenStats.to_html())
    SendMail(subject, body)
    pass

def CheckNewListings(since, maxPrice, sendMail, skipIds):
    print("Scanning new listings:")
    query = """query{
      hic_et_nunc_swap(where: {timestamp: {_gt: \"""" + since + """\"}, status: {_eq: "0"}},  order_by: {timestamp: desc}) {
       timestamp
       id
       amount
       price
       creator_id
       token {
         id
         title
         description
         royalties
         supply
         creator_id
         creator{
             name}
       }
       }
          }"""

    r = requests.post(url, json={'query': query}, timeout=60)
    json_data = json.loads(r.text)
    df = pd.json_normalize(json_data["data"]["hic_et_nunc_swap"])
    if df.empty:
        print("No new swaps")
    else:
        since = max(df['timestamp'])
        newListings = df[(df['token.creator_id'].isin(artists['token.creator_id'])) & (df['token.creator_id'] == df['creator_id']) & ~(df['id'].isin(skipIds)) & (df['price'] <= maxPrice * unit)]
        if sendMail is True:
            for index, row in newListings.iterrows():
                if(index > 0):
                    sleep(mailInterval)
                averageStats = artists[artists['token.creator_id'] == row['token.creator_id']]
                averageStats.drop(['token.creator_id', 'token.creator.name', 'lastMintTime', 'lastSecToPrim'], axis = 1, inplace = True)
                tokenStats = tokens[tokens['token.creator_id'] == row['token.creator_id']].head(20)
                tokenStats = tokenStats.reset_index(drop=True)
                tokenStats.drop(['token.creator_id', 'token.creator.name'], axis = 1, inplace = True)
                SendNewListingMail(row, averageStats, tokenStats)
                skipIds.append(row['id'])
        #print(json.dumps(json_data, indent=4))
        print("New ids: ", newListings["token.id"].tolist())
    return(since)

    
def PrintAndSleep(e, t):
    print("error thrown")
    print(str(e))
    sleep(t)
    

i = 0
skipIds = [];

    
while True:
    i += 1
    print("-------------------------------------------")
    print("Iteration: " + str(i))
    print("-------------------------------------------")
    
    if (i==1):
        since = DateUtils.GetLastHour()
        
    if ((i-1) * scanInterval) % (60 * 1080) == 0:
        while True:
            try:
                artists, tokens = ar.GetArtists(daysInInterval,numIntervals,shift)
                sleep(scanInterval)
                break
            except BaseException as e:
                PrintAndSleep(e, errorInterval)
                
    try:
        since = CheckNewListings(since, maxPrice, False if i == 1 else True, skipIds)
        skipIds.clear()
        sleep(scanInterval)
    except  BaseException as e:
        PrintAndSleep(e, errorInterval)







