import numpy as np
import deep_dive_stats.sales_db as sales_db
import deep_dive_stats.bayesian as bayesian


#optional - will only fire if you answer yes to appraiser question
try:
    import deep_dive_stats.llm_appraise as llm_appraise
except Exception:
    llm_appraise=None

def trimmed_mean(prices):
    #average after dropping the lowest and highest 10%, so
    #outliers don't move the baseline
    if not prices:
        return None
    ordered=sorted(prices)
    cut=max(1,len(ordered)//10)
    if len(ordered)>2*cut:
        ordered=ordered[cut:-cut]
    return sum(ordered)/len(ordered)

def recent_mean(cars,as_of,years=2):
    #average of sales in the two years before the relevant car sold
    cutoff=as_of-__import__("datetime").timedelta(days=years*365)
    prices=[c["price"] for c in cars if c["sale_date"] and c["sale_date"]>=cutoff]
    if len(prices)<5:
        return None
    return trimmed_mean(prices)

def ask(prompt,default):
    answer=input(f"{prompt} (blank for {default}): ").strip()
    return answer if answer else str(default)

def main():
    search=input("Model search words (ex bmw m5): ").strip().lower().split()
    model=input("BaT model code (ex BMW E39 M5, blank for none): ").strip()
    if model=="":
        model=None
    elif "," in model:
        model=[m.strip() for m in model.split(",") if m.strip()]

    exclude=input("Exclude titles containing (comma separated, blank for none): ")
    exclude_words=[w.strip().lower() for w in exclude.split(",") if w.strip()] or None

    window_size=int(ask("Number of cars per window (integer)",20))
    windows=int(ask("Number of windows (integer)",4))
    min_train=int(ask("Min number of training sales (integer)",40))
    use_llm=ask("Also score the LLM appraiser? (y/n)","n").lower().startswith("y")
    if use_llm and llm_appraise is None:
        print("LLM appraise not importable - skipping")
        use_llm=False

    comps=sales_db.load_comps(search,model=model,exclude_words=exclude_words)
    comps=[c for c in comps if c.get("price") and c.get("sale_date")]
    comps.sort(key=lambda car:car["sale_date"])
    total=len(comps)
    if total==0:
        print("No comps matched - check model code")
        return

    #figure out how many windows actually fit before running tests
    usable_windows=0
    for f in range(windows):
        train_end=total-(windows-f)*window_size
        if train_end>=min_train:
            usable_windows+=1
    if usable_windows==0:
        need=min_train+window_size
        print(f"Only {total} comps. Need at least {need} for one window")
        print("Lower iwndow size, or pool is too small to backtsest")
        return
    if usable_windows<windows:
        print(f"Only {usable_windows} of {windows} windows fit in {total} comps")
        windows=usable_windows

    print(f"\n{total} comps, {windows} windows of {window_size}, {windows*window_size} predictions to score")
    print(f"span {comps[0]["sale_date"].strftime("%m/%Y")} to {comps[-1]["sale_date"].strftime("%m/%Y")}\n")


    rows=[]
    inside=0
    scored=0
    for f in range(windows):
        train_end=total-(windows-f)*window_size
        train=comps[:train_end]
        test=comps[train_end:train_end+window_size]
        flat=trimmed_mean([c["price"] for c in train])
        print(f"window {f+1}/{windows}: train {len(train)}, test {test[0]["sale_date"].strftime("%m/%Y")}-{test[-1]["sale_date"].strftime("%m/%Y")}")

        for car in test:
            try:
                result=bayesian.predict(train,car,as_of=car["sale_date"])
            except Exception as e:
                print(f"model stopped on {(car["title"] or "?")[:36]}: {type(e).__name__}: {e}")
                continue
            if result is None:
                continue
            scored+=1
            if result["low"]<=car["price"]<=result["high"]:
                inside+=1

            recent=recent_mean(train,car["sale_date"]) or flat
            row={"actual":car["price"],"model":result["predicted"],
                 "flat":flat,"recent":recent,"title":car["title"],
                 "year":car.get("year"),"mileage":car.get("mileage"),
                 "window":f+1,}

            if use_llm:
                try:
                    guess=llm_appraise.appraise(car,train)
                except Exception as e:
                    guess=None
                    import traceback
                    print(f"appraiser failed: {type(e).__name__}")
                    traceback.print_exc()
                if guess and guess.get("estimate"):
                    row["llm"]=guess["estimate"]
                    #simple avg of the 2 is good test to see if they carry different info
                    row["combo"]=int(round(np.exp((np.log(result["predicted"])+np.log(guess["estimate"]))/2)))

            rows.append(row)
            mark=f" [{scored}] actual: ${car["price"]:>8,}  model: ${result["predicted"]:>8,}"
            if "llm" in row:
                mark+=f" llm: ${row["llm"]:>8,} "
            print(mark)

    if not rows:
        print("\nNo predictions made")
        return

    def errors(key):
        return [abs(r[key]-r["actual"])/r["actual"] for r in rows if key in r]

    def log_errors(key):
        #symmetric in ratio
        #2x high and 2x low score same
        return [abs(np.log(r[key]/r["actual"])) for r in rows if key in r]

    def show(name,key):
        e=errors(key)
        if not e:
            return
        le=log_errors(key)
        print(f"{name:16}: median: {np.median(e):>4.0%} mean: {np.mean(e):4.0%} log: {np.median(le):5.2f}")
        

    print(f"\n BACKTEST RESULTS ({len(rows)} cars, {windows} windows): ")
    show("trimmed mean:","flat")
    show("recent average:","recent")
    show("bayesian model:","model")
    show("both averaged:","combo")
    if any("llm" in r for r in rows):
        show("llm appraiser:","llm")
    want=int(round(scored*0.9))
    print(f" sell-range coverage: {inside}/{scored} inside the 90% range (want ~{want})")

    #per window, so a bad period is shown
    print("\nby window (model median):")
    for f in range(1,windows+1):
        part=[r for r in rows if r["window"]==f]
        if not part:
            continue
        me=np.median([abs(r["model"]-r["actual"])/r["actual"] for r in part])
        fe=np.median([abs(r["flat"]-r["actual"])/r["actual"] for r in part])
        flag="model" if me<fe else "FLAT "
        print(f"fold {f}: model: {me:>4.0%}, flat {fe:>4.0%}. {flag} wins.")

    #The cars the model moved furthest from the flat average are where 
    #features should pay off. A constant can't be beaten on an average car
    unusual=sorted(rows,key=lambda r:abs(r["model"]-r["flat"])/r["flat"],reverse=True)
    unusual=unusual[:max(5,scored//4)]
    model_err=[abs(r["model"]-r["actual"])/r["actual"] for r in unusual]
    flat_err=[abs(r["flat"]-r["actual"])/r["actual"] for r in unusual]
    print(f"\n unusual cars (top {len(unusual)} the model adjusted most):")
    print(f"bayesian: median {np.median(model_err):.0%}")
    print(f"trimmed mean: median {np.median(flat_err):.0%}")
    if np.median(model_err)<np.median(flat_err):
        print("features earn their keep on the cars that need them")
    else:
        print("model LOSES where it should win. something is off:")
        print("check receipt on one car in deep_dive")

    #the five worst misses, so a systematic problem is visible
    worst=sorted(rows,key=lambda r:abs(r["model"]-r["actual"])/r["actual"],reverse=True)[:5]
    print("\n worst misses (look for a pattern - all high mileage? all projects?):")
    for r in worst:
        gap=(r["model"]-r["actual"])/r["actual"]
        miles=f"{r['mileage']:,}mi" if r.get("mileage") else "?mi"
        print(f"   ${r['actual']:>7,} actual  ${r['model']:>7,} said  {gap:+.0%}  "
              f"{r.get('year') or '?'} {miles}  {(r['title'] or '')[:34]}")

if __name__=="__main__":
    main()
