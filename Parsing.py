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
    
    found=re.search(r'([\d,]+)(k?)-(miles?|mi|kilometers?|km)',t)
    if found:
        number_value=int(found.group(1))
        has_k=found.group(2)=="k"
        unit=found.group(2)

        if has_k:
            number_value=number_value*1000
        if "kilometer" in unit or "km" in unit:
            number_value=int(number_value*km_to_miles)
        return number_value

    



         


