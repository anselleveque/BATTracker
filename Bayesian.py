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
    swapped=np.array([1.0 if car.get("engine") else 0.0 for car in usable])

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
        b_modified=pm.Normal("b_modified",mu=0,sigma=1)
        b_project=pm.Normal("b_project",mu=0,sigma=1)
        b_swapped=pm.Normal("b_swapped",mu=0,sigma=1)
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
               +b_modified*modifieds
               +b_project*projects
               +b_swapped*swapped
               +b_cabriolet*is_cabriolet
               +b_targa*is_targa
               +b_sedan*is_sedan
               +b_roadster*is_roadster
               +b_time*sale_time)
        
        #Learns from real prices
        pm.Normal("observed",mu=guess,sigma=noise,observed=log_price)

        trace=pm.sample(1000,tune=1000,chains=2,cores=1,progressbar=True,random_seed=1)
        
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
        "modified":percent_effect("b_modified"),
        "project":percent_effect("b_project"),
        "engine_swap":percent_effect("b_swapped"),
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
        target_modified=1.0 if target_car.get("is_modified") else 0.0
        target_project=1.0 if target_car.get("is_project") else 0.0
        target_swapped=1.0 if target_car.get("engine") else 0.0
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
                       +draws("b_modified")*target_modified
                       +draws("b_project")*target_project
                       +draws("b_swapped")*target_swapped
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


        





