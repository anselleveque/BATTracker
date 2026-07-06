import bat_api
import parsing
import pricing
import bayesian
from main import search_term,remove_body_words

def show_percent(value):
    return f"{value*100:+.0f}%" if value else None

def count_usable(cars):
    count=0
    for car in cars:
        if car["price"] and car["year"] and car["mileage"] is not None and car["sale_date"]:
            count+=1
    return count
    
def get_comps(search,nonce,year,window=4):
    #Drop year and body style before trim
    #Never fall back to just make/model
    tiers=[]
    if year:
        tiers.append((search,year-window,year+window,f"years {year-window}-{year+window}"))
    tiers.append((search,None,None,"all years"))
    no_body=remove_body_words(search)
    if no_body!=search:
        tiers.append((no_body,None,None,"all years, body word dropped"))

    history=[]
    for s,y1,y2,label in tiers:
        print(f"Searching '{s} ({label})")
        history=bat_api.get_sale_history(s,nonce,y1,y2,max_pages=100)
        print(f" {len(history)} sales, {count_usable(history)} usable for the model")
        if count_usable(history)>=15:
            return history
    return history

def main():
    listing_url=input("URL of specific listing to price: ").strip()
    window_input=input("Year window +/- (blank for auto +4/-4): ").strip()

    if window_input=="":
        window=4
    else:
        window=int(window_input)

    print("\nGetting Listing")
    info=bat_api.get_listing_details(listing_url)
    if not info or not info["title"]:
        print("Could not read listing page")
        return
    
    title=info["title"]
    details=parsing.parse_details(info["details"])
    from_title=parsing.get_features(title,"")

    target_car={
                "year":from_title["year"],
                "mileage":details.get("mileage",from_title["mileage"]),
                "is_manual":details.get("is_manual",from_title["is_manual"]),
                "is_modified":from_title["is_modified"],
                "is_project":from_title["is_project"],
                "body":from_title["body"],
                "engine":from_title["engine"],
            }
    
    print("\nThis car: ")
    print(" title:",title[:70])
    if target_car["mileage"] is not None:
        print(f" mileage: {target_car["mileage"]:,} miles")
    print(f" manual: {target_car["is_manual"]}")
    if "engine" in details:
        print(f" engine: {details["engine"]}")
    if not details.get("original_engine",True):
        print(" replacement/non-original engine")
    if details.get("pts"):
        print(f" paint-to-sample {details.get("color","")}")
    elif "color" in details:
        print(f" color: {details["color"]}")
    if "chassis" in details:
        print(f" chassis: {details["chassis"]}")

    #Build search term from url title
    search=search_term(title)
    if search is None:
        print("\nCould not find  title to build search")
        return

    print("\nGetting Nonce")
    nonce=bat_api.get_nonce()

    print("Getting sale history")
    history=get_comps(search,nonce,target_car["year"],window)
    if len(history)<3:
        print("Too few comparable sales")
        return
    
    #Quick estimate
    estimate=pricing.estimate_price(history)
    if estimate is not None:
        print(f"\nQuick estimate from {estimate["count"]} comparable sales")
        print(f" trimmed average: ${estimate["average"]:,}")
        if estimate["recent"] is not None:
            print(f" recent average (last 2 years): ${estimate["recent"]:,}")
        print(f" range: ${estimate["low"]:,} to ${estimate["high"]:,}")

    print("\nRunning bayesian model")
    result=bayesian.predict(history,target_car)
    if result is None:
        print("Not enough data to complete model")
        return

    print(f"Bayesian prediction: ({result["describes"]}): ")
    print(f" predicted: ${result["predicted"]:,}")
    print(f" 90% range: ${result["low"]:,} to ${result["high"]:,}")
    print(f" based on {result["count"]} sales")

    effects=result["effects"]
    print("\nWhat model learned: ")
    print(f" each 10k miles more: {show_percent(effects["per_10k_miles"] if effects["per_10k_miles"] is not None else None)}")
    print(" per year newer: ",show_percent(effects["per_year"]))
    print(" manual gearbox: ",show_percent(effects["manual"]))
    print(" modified: ",show_percent(effects["modified"]))
    print(" project car: ",show_percent(effects["project"]))
    print(" engine swap: ",show_percent(effects["engine_swap"]))
    print(" cabriolet vs coupe: ",show_percent(effects["cabriolet_vs_coupe"]))
    print(" targa vs coupe: ",show_percent(effects["targa_vs_coupe"]))
    print(" sedan vs coupe: ",show_percent(effects["sedan_vs_coupe"]))
    print(" roadster vs coupe: ",show_percent(effects["roadster_vs_coupe"]))
    print(" market trend per year: ",show_percent(effects["market_per_year"]))

    

if __name__=="__main__":
    main()

