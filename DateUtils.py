# -*- coding: utf-8 -*-
"""
Created on Sun Oct  3 17:14:33 2021

@author: julia
"""

from datetime import datetime as dt
from dateutil.relativedelta import relativedelta as rd

HicDexShiftHours = -1

def ConvertToDateTime(stringTime):
    return(dt.strptime(stringTime, '%Y-%m-%dT%H:%M:%S+00:00'))

def ConvertToStringTime(dateTime):
    return(dt.strftime(dateTime,'%Y-%m-%dT%H:%M:%S+00:00'))

def GetNow():
    return (dt.strftime(dt.now()+rd(hours=HicDexShiftHours),'%Y-%m-%dT%H:%M:%S+00:00'))

def GetLastMonth():
    return (dt.strftime(dt.now()+rd(months=-1, hours=HicDexShiftHours),'%Y-%m-%dT%H:%M:%S+00:00'))

def GetNDaysPrior(n):
    return (dt.strftime(dt.now()+rd(days=-n, hours=HicDexShiftHours),'%Y-%m-%dT%H:%M:%S+00:00'))

def GetPrior(startTime,n,m):
    return (dt.strftime(ConvertToDateTime(startTime)+rd(days=-n, hours=-m),'%Y-%m-%dT%H:%M:%S+00:00'))

def GetLastHour():
    return (dt.strftime(dt.now()+rd(hours=HicDexShiftHours-1),'%Y-%m-%dT%H:%M:%S+00:00'))

def AddOneSecond(date):
    time = ConvertToDateTime(date)
    return (dt.strftime(time+rd(seconds=1),'%Y-%m-%dT%H:%M:%S+00:00'))

