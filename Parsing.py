#Pulls useful info out of BAT titles/subtitles
#Title is main title of auction
#Subtitle is selling price and date

import re
from datetime import datetime

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
    
    found=re.search(r'([\d,]+)(k?)[\s-]+(miles?|mi|kilometers?|km)\b',t)
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

    #Gear count
    gears=None
    found_gears=re.search(r'(\d+)-speed',t)
    if found_gears:
        gears=int(found_gears.group(1))

    #Trans swap said in title
    trans_swap=bool(re.search(r'\d+-speed\s+(conversion|swap)',t))


    
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
        "gears":gears,
        "trans_swap":trans_swap,
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

        #Mileage (mi)
        found_mi=re.search(r'([\d,]+)(k?)\s*miles',low)
        if found_mi:
            num=int(found_mi.group(1).replace(",",""))
            if found_mi.group(2)=="k":
                num=num*1000
            features["mileage"]=num
        
        #Mileage (km)
        found_km=re.search(r'([\d,]+)(k?)\s*kilometers',low)
        if found_km and "mileage" not in features:
            num=int(found_km.group(1).replace(",",""))
            if found_km.group(2)=="k":
                num=num*1000
            features["mileage"]=int(num*km_to_miles)

        #Engine
        if "liter" in low or "flat-" in low or "inline-" in low or low.endswith("v6") or low.endswith("v8") or low.endswith("v10") or low.endswith("v12"):
            features["engine"]=line.strip()

        #Transmission
        if "transmission" in low or "transaxle" in low or "gearbox" in low:
            if "manual" in low:
                features["is_manual"]=True
            else:
                features["is_manual"]=False

            #Gear count
            words_to_numbers={"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8}
            found_gears=re.search(r'(\d+)-speed',low)
            if found_gears:
                features["gears"]=int(found_gears.group(1))
            else:
                for word,number in words_to_numbers.items():
                    if word+"speed" in low:
                        features["gears"]=number

            #Swapped/converted gearbox
            if "replacement" in low or "conversion" in low or "swap" in low:
                features["trans_swap"]=True
        
        #Paint Color
        if re.search(r'\bpts\b',low) or "paint-to-sample" in low:
            features["pts"]=True
            color=line

            color=re.sub(r'(?i)paint[- ]to[- ]sample','',color)
            color=re.sub(r'(?i)\bpts\b','',color)
            color=re.sub(r'\bpaint\b','',color)
            features["color"]=color.strip()
        elif low.endswith("paint"):
            features["color"]=line.strip()[:-5].strip()

        #Non-original engine
        if "replacement" in low or "non-matching" in low or "-powered" in low:
            if "transmission" not in low and "transaxle" not in low and "gearbox" not in low:
                features["original_engine"]=False
        else:
            features["original_engine"]=True

        #Documents
        if "carfax" in low:
            features["has_carfax"]=True
        if "window_sticker" in low:
            features["window_sticker"]=True
        if "certificate of authenticity" in low or re.search(r'\bcoa\b',low):
            features["coa"]=True

      
        
    return features

            
                

        








    



         


