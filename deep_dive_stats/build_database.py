#Fill sale database in bulk
#Parse condition for each comp

import time
import helper_programs.bat_api as bat_api
import helper_programs.parsing as parsing
import deep_dive_stats.sales_db as sales_db
import deep_dive_stats.llm_extract as llm_extract

#Secs to wait between browser laods
DELAY=3

def build(search,year_from=None,year_to=None):
    sales_db.setup()

    print("Getting Nonce")
    nonce=bat_api.get_nonce()

    print(f"Fetching all sales for '{search}'")
    history=bat_api.get_sale_history(search,nonce,year_from,year_to,max_pages=100)
    print(f"Found {len(history)} sales. Saving basics first")
    sales_db.save_comps(history)

    urls=[car["url"] for car in history]
    total=len(urls)
    done=0
    skipped=0

    for i,url in enumerate(urls):
        #Skip loaded
        if sales_db.get_condition(url) is not None:
            skipped+=1
            continue

        print(f"[{i+1}/{total}] loading {url[:55]}")
        info=bat_api.get_listing_details(url)
        if info and info.get("description"):
            feats=llm_extract.parse_condition(info["description"])
            sales_db.save_condition(url,feats)
        else:
            sales_db.save_condition(url,{})
        done+=1

        time.sleep(DELAY)

    total_rows,enriched_rows=sales_db.stats()
    print(f"\nLoaded {done} new, skipped {skipped} already done")
    print(f"Database holds {total_rows} sales, {enriched_rows} with full detail")

def main():
    search=input("Model to load (ex Porsche 911 GT3): ").strip()
    year_from=input("Earliest year (or blank): ").strip()
    year_to=input("Latest year (or blank): ").strip()

    if year_from=="":
        year_from=None
    else:
        year_from=int(year_from)
    if year_to=="":
        year_to=None
    else:
        year_to=int(year_to)

    build(search,year_from,year_to)

if __name__=="__main__":
    main()

