#Main program to track live auctions

import json
import time
import re
from datetime import datetime, timezone
import pysher

import bat_config
import bat_api
import pricing

def clean_list(text):
    return [word.strip().lower() for word in text.split(",") if word.strip()!=""]

def matches(title,words):
    if len(words)==0:
        return True
    title=title.lower()
    return any(word in title for word in words)

def time_left(end_timestamp):
    #Turn end time into readable time left
    now=datetime.now(timezone.utc).timestamp()
    total_time=int(end_timestamp-now)
    if total_time<=0:
        return "ENDED"
    hours=total_time//3600
    minutes=(total_time%3600)//60
    seconds=total_time%60
    return f"{hours}h {minutes}m {seconds}s"

def search_term(title):
    #Separating titles into individual car model, but not trims b/c would be too narrow
    found=re.search(r'\b(19|20)\d{2}\b',title)
    if not found:
        return None
    after_year=title[found.end():].strip()

    #Words signifying end of car model
    #Keep list in mind, may need to add to it
    stop_words=[ "speed", "manual", "automatic", "project", "track",]
    
    keep=[]
    for word in after_year.split():
        clean=word.lower().strip(",")
        if clean in stop_words:
            break
        if re.match(r'\d+-',clean):
            break
        keep.append(word)
        if len(keep)>=6:
            break
        
    if len(keep)==0:
        return None

    return "".join(keep)

def get_estimate(title,keywords,nonce):
    search=search_term(title)
    if search is None:
        return None
    
    if len(keywords) > 0:
        narrow_search = search + "" + keywords[0:3]
        history = bat_api.get_sale_history(narrow_search, nonce)

        #if search is too thin, drop body style first
        if len(history)<3:
            body_styles=["coupe", "convertible", "cabriolet", "roadster", "sedan",
                        "wagon", "targa", "spider", "spyder", "touring",]
            narrow_search_words=narrow_search.split()
            no_body_words=[word for word in narrow_search_words if word.lower() not in body_styles]
            no_body_search="".join(no_body_words)
            print(f"Too few results from {narrow_search}, dropping body style")
            history=bat_api.get_sale_history(no_body_search,nonce)

            #If still too thin, drop keywords
            if len(history)<3:
                print(f"Too few results from {no_body_search}, dropping keywords")
                history=bat_api.get_sale_history(search,nonce)
        
    else:
        history=bat_api.get_sale_history(search,nonce)

    return pricing.estimate_price(history)







