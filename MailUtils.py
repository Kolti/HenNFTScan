# -*- coding: utf-8 -*-
"""
Created on Sun Oct  3 18:08:34 2021

@author: julia
"""

import smtplib
from email.mime.text import MIMEText

def SendMail(subject, body):
    sender = 'xxx'
    msg = MIMEText(body, 'html', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = 'xxx'
    smtpObj = smtplib.SMTP('smtp.office365.com', 587, timeout = 30)
    smtpObj.ehlo()
    smtpObj.starttls()
    smtpObj.login(sender, "xxx") 
    smtpObj.send_message(msg)
    smtpObj.quit()