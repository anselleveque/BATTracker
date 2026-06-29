#Pulls useful info out of BAT titles/subtitles
#Title is main title of auction
#Subtitle is selling price and date

import re
from datetime import datetime
tit="2014 Porsche 911 Turbo Coupe"
subtit="Sold for USD $90,000  on 5/29/2026"

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

def get_sale_date(subtitle):
    found=re.search(r'on (\d+/\d+/\d{4})', subtitle)
    if found:
        try:
            return datetime.strptime(found.group(1),"%m/%d/%Y")
        except ValueError:
            return None
    return None

def get_mileage(title):
    #Make everthing int miles, so need to change km to mi using ratio factor
    t=title.lower()
    km_to_miles=0.621371
    
    found=re.search(r'([\d,]+)(k?)-(miles?|mi|kilometers?|km)',t)
    if found:
        number_value=int(found.group(1).replace(",",""))
        has_k=found.group(2)=="k"
        unit=found.group(2)

        if has_k:
            number_value=number_value*1000
        if "kilometer" in unit or "km" in unit:
            number_value=int(number_value*km_to_miles)
        return number_value
    return None

def is_car(title):
    #Need to make sure that auction is actually a car
    t=title.lower()
    #Filter out non-car title words
    other_words=["tool", "wheels", "workshop manual", "manuals",
           "literature", "seats", "engine", "sign", "display model",
           "luggage", "exhaust", "hardtop", "coffee", "table",
           "shell", "gearbox"]
    
    for word in other_words:
        if word in t:
            return False
        
    if get_year(title) is None:
        return False
    return True

def get_engine(title):
    t=title.lower()
    #Find what engine is in car (mostly for american cars), but others as well
    found=re.search(r'([\w.]+)-powered',t)
    if found:
        return found.group(1)
    return None

def get_features(title,subtitle):
    #Condense all features of car
    t=title.lower()

    #Check for body type of car
    if "cabriolet" in t or "convertible" in t:
        body="cabriolet"
    elif "targa" in t:
        body="targa"
    elif "coupe" in t:
        body ="coupe"
    elif "sedan" in t:
        body="sedan"
    elif "roadster" in t:
        body="roadster"
    else:
        body="unknown"

    #Check if car is manual (won't get every case, only when in title)
    #If you want a deep dive on a car, you need to go to deep dive on an individual car
    is_manual=False
    if "manual" in t or "-speed" in t:
        is_manual=True
    
    return{
        "title":title,
        "price":get_price(subtitle),
        "year":get_year(title),
        "sale_date":get_sale_date(subtitle),
        "mileage":get_mileage(title),
        "engine":get_engine(title),
        "body":body,
        "is_manual":is_manual,
        "is_modified":"modified" in t,
        "is_project":"project" in t,
        #"url":None

    }





    



         


