#Pulls useful info out of BAT titles/subtitles
#Title is main title of auction
#Subtitle is selling price and date

import re
from datetime import datetime

def get_price(subtitle):
    found=re.search(r'\$([0-9]+)', subtitle)
    if found:
        return int(found.group(1).replace(",",""))
    return None

def get_year(title):
    found=re.search(r'\b(19|20)\d{2}\b', title)
    if found:
        return int(found.group(0))
    return None

def get_sale(subtitle):
    found=re.search(r'on (\d+/\d+/\d{4})', subtitle)
    if found:
        try:
            return datetime.strptime(found.group(1),"%m/%d/%Y")
        except ValueError:
            return None
    return None

def get_mileage(title):
    #make everthing int miles, so need to change km to mi using ratio factor
    t=title.lower()
    km_to_miles=0.621371

    #format of ##k-mile(s)/mi/kilometer(s)/km
    found=re.search(r'([\d,]+)k-(miles?|mi|kilometers?|km)',t)
    if found:
        return int(found.group(1).replace(",",""))*1000
    
    #format of #,###-mile(s)/mi
    found=re.search(r'([\d,]+)-(miles?|mi)',t)
    if found:
        return int(found.group(1).replace(",",""))
    
    #format of ##k-kilometer(s)/km
    found=re.search(r'([\d,]+)k-(kilometers?|km)',t)
    if found:
        return int(int(found.group(1).replace(",",""))*1000*km_to_miles)
    
    #format of #,###-kilometer(s)/km
    found=re.search(r'([\d,]+)-(kilometers?|km)',t)
    if found:
        return int(int(found.group(1).replace(",",""))*km_to_miles)


         


