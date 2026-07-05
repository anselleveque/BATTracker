#Main program to track live auctions

import json
import time
import re
from datetime import datetime, timezone
import pysher

import bat_config
import bat_api
import pricing
import parsing

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

    return " ".join(keep)

#Body words to locate
body_styles=["coupe", "convertible", "cabriolet", "roadster", "sedan",
            "wagon", "targa", "spider", "spyder", "touring","berlinetta",
            "barchetta",]

def remove_body_words(search):
    words=search.split()
    kept=[word for word in words if word.lower() not in body_styles]
    return " ".join(kept)

#Stores cars already found in here
_history_cache={}
def get_estimate(title,keywords,nonce):
    search=search_term(title)
    if search is None:
        return None
    
    cache_key=search+"|"+(keywords[0] if keywords else "")
    if cache_key in _history_cache:
        return _history_cache[cache_key]
    if len(keywords) > 0:
        narrow_search = search + " " + keywords[0]
        history = bat_api.get_sale_history(narrow_search, nonce)

        #if search is too thin, drop body style first
        if len(history)<3:
            no_body_search=remove_body_words(search)+" "+keywords[0]
            print(f"Too few results from {narrow_search}, dropping body style")
            history=bat_api.get_sale_history(no_body_search,nonce)

            #If still too thin, drop keywords
            if len(history)<3:
                broad_search=remove_body_words(search)
                print(f"Too few results from {no_body_search}, dropping keywords")
                history=bat_api.get_sale_history(broad_search,nonce)
        
    else:
        history=bat_api.get_sale_history(search,nonce)
        #Try without keywords but with body
        if len(history)<3:
            no_keyword_search=remove_body_words(search)
            print(f"Too few results from {search}, dropping keywords from search")
            history=bat_api.get_sale_history(no_keyword_search,nonce)
    result=pricing.estimate_price(history)
    _history_cache[cache_key]=result
    return result

def main():
    brands=clean_list(input("Brands to watch (comma separated, or blank): "))
    models=clean_list(input("Models to watch (comma separated, or blank): "))
    keywords=clean_list(input("Keywords like manual/modified to add (comma separated, or blank): "))

    print("\nGetting nonce")
    nonce=bat_api.get_nonce()

    print("\nLoading auctions")
    auctions=bat_api.get_live_auctions()

    #Filter cars for input
    watched=[]
    for item in auctions:
        title=item["title"]
    
        if not item.get("active"):
            continue
        if not parsing.is_car(title):
            continue
        if not matches(title,brands):
            continue
        if not matches(title,models):
            continue
        if not matches(title,keywords):
            continue

        estimate=get_estimate(title,keywords,nonce)
        print(" checked", title[:50])

        car={
            "title":title,
            "url":item["url"],
            "channel":item["pusher"],
            "current_bid":item["current_bid"],
            "end":item["timestamp_end"],
            "estimate":estimate,
        }
        watched.append(car)

    if len(watched)==0:
        print("No live auctions watched")
        return
    
    print_all(watched) #Show start state

    print("Connecting to server for updates")
    listen_for_bids(watched)

def get_end_time(car):
    return car["end"]

def print_all(watched):
    print("\nCurrent Auctions")
    watched.sort(key=get_end_time)

    for car in watched:
        label=pricing.deal_label(car["current_bid"], car["estimate"], bat_config.DEAL_THRESHOLD)
        bid_text="$"+format(car["current_bid"], ",")
        print(f"\n{time_left(car["end"])} | {bid_text} | {car["title"][:50]}")
        print(" ",label)
        print(" ",car["url"])
    print()

def listen_for_bids(watched):
    pusher=pysher.Pusher(bat_config.PUSHER_KEY,cluster=bat_config.PUSHER_ClUSTER)

    def on_connect(data):
        for car in watched:
            channel=pusher.subscribe(car["channel"])
            channel.bind("metadata-updated",lambda raw, c=car:handle_bid(raw,c))
        print(f"Watching {len(watched)} auctions")
    
    pusher.connection.bind("pusher:connection_established", on_connect)
    pusher.connect()

    #Keep cycling program so it doesn't close
    try:
        while True:
            time.sleep(30)
            print_all(watched)
    except KeyboardInterrupt:
        print("\nStopped")
    
def handle_bid(raw,car):
    #Called by pusher when new bid happens
    data=json.loads(raw)
    card=data.get("listing_card_data",{})

    if card.get("current_bid"):
        car["current_bid"]=card["current_bid"]
    if card.get("timestamp_end"):
        car["end"]=card["timestamp_end"]
    
    label=pricing.deal_label(car["current_bid"],car["estimate"],bat_config.DEAL_THRESHOLD)
    bid_text="$"+format(car["current_bid"], ",")
    print(f"New Bid: {time_left(car["end"])} | {bid_text} | {car["title"][:50]}")
    print(" ",label)

main()







 


