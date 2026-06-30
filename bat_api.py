import requests
import json
import time
import re
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

import bat_config
import parsing

def get_nonce():
    #BAT needs nonce to allow a search
    #Located in <script> tag on auctions page
    page=requests.get(bat_config.AUCTIONS_URL,headers=bat_config.HEADERS)
    soup=BeautifulSoup(page.text,"html.parser")

    for script in soup.find_all("script"):
        if script.string and "X-WP-Nonce" in script.string:
            found=re.search(r'X-WP-Nonce["\s:]+["\']([a-f0-9]+)["\']',script.string)
            if found:
                return found.group(1)
    return None

def get_sale_history(search,nonce,year_from=None,year_to=None):
    #Pulls every past sold listing that matches search
    headers=bat_config.HEADERS.copy()
    headers["X-WP-Nonce"]=nonce

    sold_cars=[]
    page=1

    while True:
        response=requests.get(bat_config.KEYWORD_API,headers=headers,params={
            #Params are URL query string
            "page":page,
            "s":search,
            "results":"items"
        })
        if response.status_code!=200:
            break

        data=response.json()
        items=data["items"]
        last_page=data["page_maximum"]

        for item in items:
            title=item["title"]
            subtitle=item.get("subtitle","")

            if "sold for" not in subtitle.lower():
                continue
            if not parsing.is_car(title):
                continue

            features=parsing.get_features(title,subtitle)
            features["url"]=item["url"]

            price=features["price"]
            year=features["year"]

            if price is None or price<500:
                continue

            if year is not None:
                if year is not None and year<year_from:
                    continue
                if year is not None and year>year_to:
                    continue

            sold_cars.append(features)

        if page>=last_page:
            break
        page=page+1
        time.sleep(0.3)

    return sold_cars

def get_live_auctions():
    #Gets live auctions from BAT auctions page

    with sync_playwright as p:
        browser=p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"],
        )
        context=browser.new_context(
            user_agent=bat_config.BROWSER_USER_AGENT,
            viewport={"width":1200,"height":800},
        )

        #Hide fact browser is automated from BAT by setting navigator.webdriver to undefined
        context.add_init_script(
            "Object.defineProperty(navigator,'webdriver', {get:()=>undefined})"
        )

        page=context.new_page()
        page.goto(bat_config.AUCTIONS_URL,wait_until="domcontentloaded",timeout=60000)
        #Wait until all content has loaded correctly
        try:
            page.wait_for_function("()=>window.auctionsCurrentInitialData!==undefined",timeout=30000)
        except:
            print("Auction data did not load")
            browser.close()
            return []
        
        raw=page.evaluate("()=>JSON.stringify(window.auctionsCurrentInitalData)")
        browser.close()
    if not raw:
        print("Auction data not found on page")
        return []
    
    return json.loads(raw)["items"]

        

        

