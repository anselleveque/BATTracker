import helper_programs.bat_api as bat_api
import helper_programs.parsing as parsing
import helper_programs.pricing as pricing
import deep_dive_stats.bayesian as bayesian
import deep_dive_stats.sales_db as sales_db
import deep_dive_stats.llm_extract as llm_extract
from live_tracker.main import search_term,remove_body_words

def show_percent(value):
    if not value:
        return None
    try:
        num_value=float(value)
        return f"{num_value*100:+.0f}%"
    except (ValueError,TypeError):
        return str(value)

def count_flaws(condition):
    if "flaw_count" in condition:
        return condition["flaw_count"]
    flaws=condition.get("notable_flaws")
    if flaws is None:
        return None
    return len(flaws)

def count_usable(cars):
    count=0
    for car in cars:
        if car["price"] and car["year"] and car["mileage"] is not None and car["sale_date"]:
            count+=1
    return count
    
def get_comps(search,nonce,year,top_window=4,bottom_window=4):
    #Drop year and body style before trim
    #Never fall back to just make/model
    tiers=[]
    if year:
        tiers.append((search,year-bottom_window,year+top_window,f"years {year-bottom_window}-{year+top_window}"))
    tiers.append((search,None,None,"all years"))
    no_body=remove_body_words(search)
    if no_body!=search:
        tiers.append((no_body,None,None,"all years, body word dropped"))

    history=[]
    for s,y1,y2,label in tiers:
        print(f"Searching '{s}' ({label})")
        history=bat_api.get_sale_history(s,nonce,y1,y2,max_pages=100)
        print(f" {len(history)} sales, {count_usable(history)} usable for the model")
        if count_usable(history)>=15:
            return history
    return history

def show_nearest(history,target_car,how_many=5):
    #Most similar sales
    if target_car["mileage"] is None:
        return
    with_mileage=[car for car in history if car.get("mileage") and car.get("price")]
    if not with_mileage:
        return
    def distance(car):
        miles_gap=abs(car["mileage"]-target_car["mileage"])
        year_gap=abs((car.get("year") or 0)-(target_car.get("year") or 0))
        #Year apart counts like 2.5k miles4
        return miles_gap+year_gap*2500
    with_mileage.sort(key=distance)
    print("\nClosest comps to this car: ")
    for car in with_mileage[:how_many]:
        date=car["sale_date"].strftime("%m/%Y") if car.get("sale_date") else "?"
        print(f" ${car["price"]:>7,} {car["year"]} {car["mileage"]:>7,} mi {date} {car["title"][:38]}")


def main():
    sales_db.setup()

    listing_url=input("URL of specific listing to price: ").strip()
    top_window_input=input("Year window + (blank for auto +4): ").strip()
    bottom_window_input=input("Year window - (blank for auto -4): ").strip()
    MAX_COMP_AGE=input("Maximum age of listings to compare to (blank for 5 y/o): ").strip()
    
    if MAX_COMP_AGE=="":
        MAX_COMP_AGE=5
    else:
        MAX_COMP_AGE=int(MAX_COMP_AGE)

    if top_window_input=="":
        top_window=4
    else:
        top_window=int(top_window_input)
    if bottom_window_input=="":
        bottom_window=4
    else:
        bottom_window=int(bottom_window_input)

    print("\nGetting Listing")
    info=bat_api.get_listing_details(listing_url)
    if not info or not info["title"]:
        print("Could not read listing page")
        return
    
    title=info["title"]
    details=parsing.parse_details(info["details"])
    from_title=parsing.get_features(title,"")

    #Condition for this car
    #Checks database first
    target_condition=sales_db.get_condition(listing_url)
    if target_condition is None:
        target_condition={}
        if info.get("description"):
            parsed=llm_extract.parse_condition(info["description"])
            if parsed:
                target_condition=parsed
                sales_db.save_condition(listing_url,target_condition,info.get("model"),info["description"],details.get("chassis"))

    target_car={
                "condition_grade":target_condition.get("condition_grade"),
                "year":from_title["year"],
                "mileage":details.get("mileage",from_title["mileage"]),
                "is_manual":details.get("is_manual",from_title["is_manual"]),
                "gears":from_title["gears"],
                "is_modified":from_title["is_modified"],
                "is_project":from_title["is_project"],
                "body":from_title["body"],
                "engine":from_title["engine"],
                "condition_grade":target_condition.get("condition_grade"),
                "matching_engine":target_condition.get("matching_engine"),
                "matching_trans":target_condition.get("matching_trans"),
                "flaw_count":count_flaws(target_condition),
            }
    
    print("\nThis car: ")
    print(" title:",title[:70])
    target_model=info.get("model")
    if target_model:
        print(f" model: {target_model}")
    if target_car["condition_grade"]:
        print(f" condition: {target_car["condition_grade"]}")
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
        print("\nCould not find year in title to build search")
        return
    
    #Try local db
    year=target_car["year"]
    search_words=search.lower().split()
    if year:
        history=sales_db.load_comps(search_words,year-bottom_window,year+top_window,target_model,max_age_years=MAX_COMP_AGE)
    else:
        history=sales_db.load_comps(search_words,None,None,target_model,max_age_years=MAX_COMP_AGE)

    
    if len(history)<15:
        print(f"Few sales in last {MAX_COMP_AGE}, using all years")
        if year:
            history=sales_db.load_comps(search_words,year-bottom_window,year+top_window,target_model)
        else:
            history=sales_db.load_comps(search_words,None,None,target_model)

    if len(history)>3:
        print(f"Using {len(history)} sales from db")
        
    else:
        print(f"\nDB has too few/none for car, fetching live")
        print("\nRun build_database.py on this model to get condition info")
        print("\nGetting Nonce")
        nonce=bat_api.get_nonce()
        history=get_comps(search,nonce,year,top_window,bottom_window)
        sales_db.save_comps(history)
    
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
        show_nearest(history,target_car)

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
    print(f" each 10k miles more (at typical miles): {show_percent(effects["per_10k_miles"] if effects["per_10k_miles"] is not None else "No miles data")}")
    print(f" per year newer: {show_percent(effects["per_year"])}")
    print(f" per extra gear: {show_percent(effects["per_gear"])}")
    print(f" per condition step: {show_percent(effects["per_condition_step"] if effects["per_condition_step"] is not None else "No condition data")}")
    print(f" matching engine: {show_percent(effects["matching_engine"] if effects["matching_engine"] is not None else "No matching engine data")}")
    print(f" matching trans: {show_percent(effects["matching_trans"] if effects["matching_trans"] is not None else "No matching trans data")}")
    print(f" per flaw noted: {show_percent(effects["per_flaw"] if effects["per_flaw"] is not None else "No flaw data")}")
    print(f" manual gearbox: {show_percent(effects["manual"])}")
    print(f" modified: {show_percent(effects["modified"])}")
    print(f" project car: {show_percent(effects["project"])}")
    print(f" cabriolet vs coupe: {show_percent(effects["cabriolet_vs_coupe"])}")
    print(f" targa vs coupe: {show_percent(effects["targa_vs_coupe"])}")
    print(f" sedan vs coupe: {show_percent(effects["sedan_vs_coupe"])}")
    print(f" roadster vs coupe: {show_percent(effects["roadster_vs_coupe"])}")
    print(f" market trend per year: {show_percent(effects["market_per_year"])}")

    

if __name__=="__main__":
    main()

