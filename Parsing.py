#Pulls useful info out of BAT titles/subtitles
#Title is main title of auction
#Subtitle is selling price and date

import re
from datetime import datetime
tit="2014 Porsche 911 Turbo Coupe"
subtit="Sold for USD $90,000  on 5/29/2026"

def get_price(subtitle):
    found=re.search(r'\$([0-9,]+)', subtitle)
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
        unit=found.group(3)

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
    elif "roadster" in t or "spyder" in t or "spider" in t:
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
        "url":None

    }

def parse_details(text):
    #Search individual "listing details" for info on the car
    #Used for deep dive
    if not text:
        return {}
    
    km_to_miles=0.621371
    features={}

    for line in text.split("\n"):
        low=line.lower().strip()

        #Chassis/vin number
        if low.startswith("chassis"):
            parts=line.split(":",1)
            if len(parts)==2:
                features["chassis"]=parts[1].strip()

        #Mileage
        found_mileage=re.search(r'([\d,]+)(k?)\s*kilometers',low)
        if found_mileage and "mileage" not in features:
            num=int(found_mileage.group(1).replace(",",""))
            if found_mileage.group(2)=="k":
                num=num*1000
            features["mileage"]=int(km_to_miles)

        #Engine
        if "liter" in low or "flat-" in low or "inline-" in low or low.endswith("v6") or low.endswith("v8") or low.endswith("v10") or low.endswith("v12"):
            features["engine"]=line.strip()

        #Transmission
        if "manual" in low:
            features["is_manual"]=True
        elif "automatic" in low:
            features["is_auto"]=True
        else:
            features["is_manual"]=False
            features["is_auto"]=False

        #Paint Color
        if "pts" in low or "paint-to-sample" in low:
            found_paint=re.search(r'^(?:pts|paint-to-sample)?\s*\b([\w\s]+)',low)
            if found_paint:
                features["pts"]=True
                features["color"]=found_paint.group(1).strip()
        elif low.endswith("paint"):
            features["color"]=line.strip()[:-5].strip()

        #Non-original engine
        if "replacement" in low or "non-matching" in low:
            features["original_engine"]=False

        #Documents
        if "carfax" in low:
            features["has_carfax"]=True
        if "window_sticker" in low:
            features["window_sticker"]=True
        if "certificate of authenticity" in low or re.search(r'\boca\b',low):
            features["coa"]=True
        
    return features

            
                

        








    



         


