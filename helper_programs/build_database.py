#Fill sale database in bulk
#Parse condition for each comp

import time
import helper_programs.bat_api as bat_api
import helper_programs.parsing as parsing
import deep_dive_stats.sales_db as sales_db
import deep_dive_stats.llm_extract as llm_extract


#Secs to wait between browser laods
DELAY=1

def build(search,year_from=None,year_to=None):
    sales_db.setup()

    print("Getting Nonce")
    nonce=bat_api.get_nonce()

    print(f"Fetching all sales for '{search}'")
    history=bat_api.get_sale_history(search,nonce,year_from,year_to,max_pages=100)

    #Skip other titles
    skip=input("Skip titles containing (comma separated, blank for none): ")
    if skip:
        bad=[w.strip().lower() for w in skip.split(",") if w.strip()]
        before=len(history)
        history=[c for c in history if not any(w in (c.get("title") or "").lower() for w in bad)]
        print(f"dropped {before-len(history)} listings matching {bad}")
    print(f"Found {len(history)} sales. Saving basics first")
    sales_db.save_comps(history)

    urls=[car["url"] for car in history]
    total=len(urls)
    done=0
    skipped=0
    failed=0

    for i,url in enumerate(urls):
        #Skip loaded
        if sales_db.get_condition(url) is not None:
            skipped+=1
            continue
        
        print(f"[{i+1}/{total}] loading {url[:55]}")
        info=None
        try:
            info=bat_api.get_listing_details(url)
        except Exception as e:
            print(f" page failed to load, will retry next run: {type(e).__name__}")
            failed+=1
            time.sleep(DELAY)

        if info and info.get("description"):
            feats=llm_extract.parse_condition(info["description"])
            if feats:
                chassis=None
                if info.get("details"):
                    chassis=parsing.parse_details(info["details"]).get("chassis")
                sales_db.save_condition(url,feats,info.get("model"),info["description"],chassis,info.get("details"))
                done+=1
            else:
                print(" parse failed, retrying next run")
                failed+=1
        elif info:
            sales_db.save_condition(url,{},info.get("model"),"",None,info.get("details"))
            done+=1
        else:
            print(" page returned nothing, retrying next run")
            failed+=1

        time.sleep(DELAY)

    total_rows,enriched_rows=sales_db.stats()
    print(f"\nLoaded {done} new, skipped {skipped} already done, failed {failed}")
    return done,skipped,failed

def build_many(searches):
    #Run build() on each model in list
    sales_db.setup()
    print(f"Loading {len(searches)} models")

    results=[]
    for search in searches:
        try:
            done,skipped,failed=build(search)
            results.append((search,done,skipped,failed))
        except Exception as e:
            print(f" {search} failed:{type(e).__name__}-{e}")
            results.append((search,0,0,0))

    print(f"\nAll models loaded")
    total_rows,enriched_rows=sales_db.stats()
    for search,done,skipped,failed in results:
        note=f"{done} new, {skipped} already done"
        if failed:
            note+=f", {failed} failed (re-run to retry)" 
        print(f" {search}:{note}")
    print(f"Database holds {total_rows} sales, {enriched_rows} with full detail")

def main():
    print("Models to load, one line at a time (ex Porsche 911 GT3)")
    print("Press enter on blank line to end model list")
    print("To input a file, type file\n")

    searches=[]
    while True:
        line=input("Model (or blank to start): ").strip()
        if line=="":
            break
        elif line=="file":
            file=input("Input file name, including extension: ")
            with open(file,"r") as f:
                lines=f.readlines()
            cleaned_lines=[line.strip() for line in lines]
            for l in cleaned_lines:
                searches.append(l)
        else:
            searches.append(line)

    if not searches:
        print("No models entered")
        return
    
    print(f"\n {len(searches)} models: {', '.join(searches)}")
    build_many(searches)
    

if __name__=="__main__":
    main()

