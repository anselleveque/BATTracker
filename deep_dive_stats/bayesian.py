#Deep dive price model
#Learns how much each feature of car changes price
#Adds or takes off of price based on features

from datetime import datetime
import numpy as np
import pymc as pm

def predict(cars, target_car=None):
    #Only use cars that have every feature
    #Mileage is not required, as many car titles omit
    usable=[]
    for car in cars:
        if car["price"] and car["year"] and car["sale_date"]:
            usable.append(car)
            
    if len(usable)<15:
        print("Not enough data points")
        return None
    
    #Get each feature in a list
    #Center year and mileage near zero for model behaivor

    prices=[car["price"] for car in usable]
    years=np.array([car["year"] for car in usable],dtype=float)
    mileages_raw=[car.get("mileage") for car in usable]
    known_mileage=[m for m in mileages_raw if m is not None]
    mileage_known_count=len(known_mileage)
    if mileage_known_count>0:
        mileage_fill=sum(known_mileage)/mileage_known_count
    else:
        mileage_fill=0.0
    mileages=np.array([m if m is not None else mileage_fill for m in mileages_raw], dtype=float)
    dates=[car["sale_date"] for car in usable]
    manuals=np.array([1.0 if car["is_manual"] else 0.0 for car in usable])
    modifieds=np.array([1.0 if car["is_modified"] else 0.0 for car in usable])
    projects=np.array([1.0 if car.get("is_project") else 0.0 for car in usable])

    #Gear count from titles, cars that don't say dnt pull average
    gears_raw=[car.get("gears") for car in usable]
    known_gears=[g for g in gears_raw if g is not None]
    if len(known_gears)>0:
        gears_mean=sum(known_gears)/len(known_gears)
    else:
        gears_mean=0.0
    gears=np.array([g if g is not None else gears_mean for g in gears_raw],dtype=float)
    #Per extra gear
    gears_centered=gears-gears_mean

    #Grades are scored 0-4
    grade_map={"project":0,"driver":1,"decent":2,"excellent":3,"concours":4}
    cond_raw=[grade_map.get(car.get("condition_grade")) for car in usable]
    known_cond=[c for c in cond_raw if c is not None]
    cond_known_count=len(known_cond)
    if cond_known_count>0:
        cond_mean=sum(known_cond)/cond_known_count
    else:
        cond_mean=0
    condition=np.array([c if c is not None else cond_mean for c in cond_raw],dtype=float)
    condition_centered=condition-cond_mean

    #Matching engine
    match_eng_raw=[car.get("matching_engine") for car in usable]
    match_eng_known=[e for e in match_eng_raw if e is not None]
    match_eng_count=len(match_eng_known)
    if match_eng_count>0:
        match_eng_mean=sum(match_eng_known)/match_eng_count
    else:
        match_eng_mean=0.0
    match_eng=np.array([e if e is not None else match_eng_mean for e in match_eng_raw],dtype=float)
    matching_eng_centered=match_eng-match_eng_mean

    #Matching trans
    match_trans_raw=[car.get("matching_trans") for car in usable]
    match_trans_known=[t for t in match_trans_raw if t is not None]
    match_trans_count=len(match_trans_known)
    if match_trans_count>0:
        match_trans_mean=sum(match_trans_known)/match_trans_count
    else:
        match_trans_mean=0.0
    match_trans=np.array([t if t is not None else match_trans_mean for t in match_trans_raw],dtype=float)
    matching_trans_centered=match_trans-match_trans_mean

    #Flaw count
    flaw_raw=[car.get("flaw_count") for car in usable]
    known_flaw=[f for f in flaw_raw if f  is not None]
    flaw_known_count=len(known_flaw)
    if flaw_known_count>0:
        flaw_mean=sum(known_flaw)/flaw_known_count
    else:
        flaw_mean=0.0
    flaws=np.array([f if f is not None else flaw_mean for f in flaw_raw],dtype=float)
    flaws_centered=flaws-flaw_mean

    #Coupe and unknown are baselines for body type
    is_cabriolet=np.array([1.0 if car["body"]=="cabriolet" else 0.0 for car in usable])
    is_targa=np.array([1.0 if car["body"]=="targa" else 0.0 for car in usable])
    is_sedan=np.array([1.0 if car["body"]=="sedan" else 0.0 for car in usable])
    is_roadster=np.array([1.0 if car["body"]=="roadster" else 0.0 for car in usable])

    log_price=np.log(prices)

    #Make sale dates years since first sale to see market movement
    earliest=min(dates)
    sale_time=np.array([(d-earliest).days/365.0 for d in dates])

    #Avoid div by 0
    year_std=years.std()
    if year_std==0:
        year_std=1
    mileage_std=mileages.std()
    if mileage_std==0:
        mileage_std=1

    year_scaled=(years-years.mean())/year_std
    mileage_scaled=(mileages-mileages.mean())/mileage_std

    with pm.Model() as model:
        #Things model will learn
        intercept=pm.Normal("intercept",mu=log_price.mean(),sigma=2)
        b_year=pm.Normal("b_year",mu=0,sigma=1)
        b_mileage=pm.Normal("b_mileage",mu=0,sigma=1)
        b_manual=pm.Normal("b_manual",mu=0,sigma=1)
        b_gears=pm.Normal("b_gears",mu=0,sigma=1)
        b_condition=pm.Normal("b_condition",mu=0,sigma=1)
        b_matching_eng=pm.Normal("b_matching_eng",mu=0,sigma=1)
        b_matching_trans=pm.Normal("b_matching_trans",mu=0,sigma=1)
        b_flaws=pm.Normal("b_flaws",mu=0,sigma=1)
        b_modified=pm.Normal("b_modified",mu=0,sigma=1)
        b_project=pm.Normal("b_project",mu=0,sigma=1)
        b_cabriolet=pm.Normal("b_cabriolet",mu=0,sigma=1)
        b_targa=pm.Normal("b_targa",mu=0,sigma=1)
        b_sedan=pm.Normal("b_sedan",mu=0,sigma=1)
        b_roadster=pm.Normal("b_roadster",mu=0,sigma=1)
        b_time=pm.Normal("b_time",mu=0,sigma=1)
        noise=pm.HalfNormal("noise",sigma=1)

        #Model guess for car's log price
        guess=(intercept
               +b_year*year_scaled
               +b_mileage*mileage_scaled
               +b_manual*manuals
               +b_gears*gears_centered
               +b_condition*condition_centered
               +b_matching_eng*matching_eng_centered
               +b_matching_trans*matching_trans_centered
               +b_flaws*flaws_centered
               +b_modified*modifieds
               +b_project*projects
               +b_cabriolet*is_cabriolet
               +b_targa*is_targa
               +b_sedan*is_sedan
               +b_roadster*is_roadster
               +b_time*sale_time)
        
        #Learns from real prices
        pm.Normal("observed",mu=guess,sigma=noise,observed=log_price)

        trace=pm.sample(1000,tune=1000,chains=4,cores=1,progressbar=True,random_seed=1)
        
    samples=trace.posterior

    def draws(name):
        #All sample values for one learned number in flat array
        return samples[name].values.flatten()
    
    def percent_effect(name,scale=1.0):
        middle=np.median(draws(name))
        return float(np.exp(middle*scale)-1)

    #What model predicts each feature is worth
    effects={
        #Standardize year and mileage to per 1 year newer, 10k miles more
        "per_year":percent_effect("b_year",1.0/year_std),
        "per_10k_miles":percent_effect("b_mileage",10000/mileage_std) if mileage_known_count>=8 else None,
        "manual":percent_effect("b_manual"),
        "per_gear":percent_effect("b_gears"),
        "per_condition_step":percent_effect("b_condition") if cond_known_count>=8 else None,
        "matching_engine":percent_effect("b_matching_eng") if match_eng_count>=8 else None,
        "matching_trans":percent_effect("b_matching_trans") if match_trans_count>=8 else None,
        "per_flaw":percent_effect("b_flaws") if flaw_known_count>=8 else None,
        "modified":percent_effect("b_modified"),
        "project":percent_effect("b_project"),
        "cabriolet_vs_coupe":percent_effect("b_cabriolet"),
        "targa_vs_coupe":percent_effect("b_targa"),
        "sedan_vs_coupe":percent_effect("b_sedan"),
        "roadster_vs_coupe":percent_effect("b_roadster"),
        "market_per_year":percent_effect("b_time")
    }

    if target_car is None:
        #If no target car, typical stock coupe 1 year from most recent sale
        predicted_log=draws("intercept")+draws("b_time")*(sale_time.max()+1.0)
        describes="a typical stock coupe 1 year from latest sale"

    else:
        #Specific car's value at today's date
        if target_car.get("year"):
            target_year=(target_car["year"]-years.mean())/year_std
        else:
            target_year=0.0

        if target_car.get("mileage") is not None and mileage_known_count>=8:
            target_mileage=(target_car["mileage"]-mileages.mean())/mileage_std
        else:
            target_mileage=0.0
        
        target_manual=1.0 if target_car.get("is_manual") else 0.0
        if target_car.get("gears") is not None:
            target_gears=target_car["gears"]-gears_mean
        else:
            target_gears=0.0

        target_grade=grade_map.get(target_car.get("condition_grade"))
        if target_grade is not None and cond_known_count>=8:
            target_condition=target_grade-cond_mean
        else:
            target_condition=0.0

        if target_car.get("matching_engine") is not None and match_eng_count>=8:
            target_engine_match=float(target_car.get("matching_engine"))-match_eng_mean
        else:
            target_engine_match=0.0

        if target_car.get("matching_trans") is not None and match_trans_count>=8:
            target_trans_match=float(target_car.get("matching_trans"))-match_trans_mean
        else:
            target_trans_match=0.0
        
        if target_car.get("flaw_count") is not None and match_trans_count>=8:
            target_flaws=float(target_car.get("flaw_count"))-flaw_mean
        else:
            target_flaws=0.0

        target_modified=1.0 if target_car.get("is_modified") else 0.0
        target_project=1.0 if target_car.get("is_project") else 0.0
        target_cabriolet=1.0 if target_car.get("body")=="cabriolet" else 0.0
        target_targa=1.0 if target_car.get("body")=="targa" else 0.0
        target_sedan=1.0 if target_car.get("body")=="sedan" else 0.0
        target_roadster=1.0 if target_car.get("body")=="roadster" else 0.0

        time_now=(datetime.now()-earliest).days/365.0

        predicted_log=(draws("intercept")
                       +draws("b_year")*target_year
                       +draws("b_mileage")*target_mileage
                       +draws("b_manual")*target_manual
                       +draws("b_gears")*target_gears
                       +draws("b_condition")*target_condition
                       +draws("b_matching_eng")*target_engine_match
                       +draws("b_matching_trans")*target_trans_match
                       +draws("b_flaws")*target_flaws
                       +draws("b_modified")*target_modified
                       +draws("b_project")*target_project
                       +draws("b_cabriolet")*target_cabriolet
                       +draws("b_targa")*target_targa
                       +draws("b_sedan")*target_sedan
                       +draws("b_roadster")*target_roadster
                       +draws("b_time")*time_now)
        describes="this specific car at today's date"

    predicted_price=np.exp(predicted_log)

    return{
        "predicted":int(np.median(predicted_price)),
        "low":int(np.percentile(predicted_price,5)),
        "high":int(np.percentile(predicted_price,95)),
        "count":len(usable),
        "effects":effects,
        "describes":describes,
    }


        





