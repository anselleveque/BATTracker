#Deep dive price model
#Learns how much each feature of car changes price
#Adds or takes off of price based on features

from datetime import datetime
from collections import Counter
import numpy as np
import pymc as pm
import helper_programs.parsing as parsing

def predict(cars, target_car=None,as_of=None):
    #Only use cars that have every feature
    #Mileage is not required, as many car titles omit
    usable=[]
    for car in cars:
        if car.get("price") and car.get("year") and car.get("sale_date"):
            usable.append(car)
            
    if len(usable)<15:
        print("Not enough data points")
        return None
    
    def usable_features(values):
        known=[v for v in values if v is not None]
        if len(known)<8:
            return False
        minority=min(sum(known),len(known)-sum(known))
        if minority<8:
            return False
        if minority/len(known)<0.10:
            return False
        return True
    
    def binary_feature(values):
        ok=usable_features(values)
        known=[v for v in values if v is not None]
        if len(known)>0:
            mean=sum(known)/len(known)
        else:
            mean=0.0
        arr=np.array([v if v is not None else mean for v in values],dtype=float)
        centered=arr-mean
        if not ok:
            centered=centered*0.0
        return centered,mean,ok
    
    def target_binary(value,mean,ok):
        #Centered target value for a binary 1/0 feature
        if value is None or not ok:
            return 0.0
        return float(value)-mean
    

    #Get each feature in a list
    #Center near zero for model behaivor
    prices=[car["price"] for car in usable]
    years=np.array([car["year"] for car in usable],dtype=float)
    dates=[car["sale_date"] for car in usable]

    #Log mileage
    mileages_raw=[car.get("mileage") for car in usable]
    known_mileage=[m for m in mileages_raw if m is not None and m>0]
    mileage_known_count=len(known_mileage)
    mileage_ok=mileage_known_count>=8
    if mileage_known_count>0:
        log_mileage_fill=float(np.mean(np.log(known_mileage)))
        median_mileage=float(np.median(known_mileage))
    else:
        log_mileage_fill=0.0
        median_mileage=50000.0
    log_mileage=np.array([np.log(m) if (m is not None and m>0) else log_mileage_fill for m in mileages_raw])
    log_mileage_centered=log_mileage-log_mileage_fill
    if not mileage_ok:
        log_mileage_centered=log_mileage_centered*0.0

    #Gear count from titles, cars that don't say dnt pull average
    gears_raw=[car.get("gears") for car in usable]
    known_gears=[g for g in gears_raw if g is not None]
    gears_known_count=len(known_gears)
    gears_ok=gears_known_count>=8 and len(set(known_gears))>1
    if gears_known_count>0:
        gears_mean=sum(known_gears)/gears_known_count
    else:
        gears_mean=0.0
    gears=np.array([g if g is not None else gears_mean for g in gears_raw],dtype=float)
    #Per extra gear
    gears_centered=gears-gears_mean
    if not gears_ok:
        gears_centered=gears_centered*0.0

    #Grades are scored 0-2, project is binary since it is a big price drop
    grade_map={"driver":0,"excellent":1,"concours":2}
    cond_raw=[grade_map.get(car.get("condition_grade")) for car in usable]
    known_cond=[c for c in cond_raw if c is not None]
    cond_known_count=len(known_cond)
    cond_ok=cond_known_count>=8
    if cond_known_count>0:
        cond_mean=sum(known_cond)/cond_known_count
    else:
        cond_mean=0
    condition=np.array([c if c is not None else cond_mean for c in cond_raw],dtype=float)
    condition_centered=condition-cond_mean
    if not cond_ok:
        condition_centered=condition_centered*0.0

    #Condition is also mapped to a 1-10 scale
    #Finer than scale, may seperate cars otherwise lumped together
    score_raw=[car.get("condition_score") for car in usable]
    known_score=[s for s in score_raw if s is not None]
    score_known_count=len(known_score)
    score_ok=score_known_count>=8
    if score_known_count>0:
        score_mean=sum(known_score)/score_known_count
    else:
        score_mean=0.0
    score=np.array([s if s is not None else score_mean for s in score_raw],dtype=float)
    score_centered=score-score_mean
    if not score_ok:
        score_centered=score_centered*0.0

    #Only track major flaws, minor flaws are noise
    major_raw=[car.get("major_flaw_count") for car in usable]
    known_major=[f for f in major_raw if f is not None]
    major_known_count=len(known_major)
    major_ok=major_known_count>=8
    if major_known_count>0:
        major_mean=sum(known_major)/major_known_count
    else:
        major_mean=0.0
    major=np.array([f if f is not None else major_mean for f in major_raw],dtype=float)
    major_centered=major-major_mean
    if not major_ok:
        major_centered=major_centered*0.0
        
    #Yes/no features go through guard and centering
    BINARY_FEATURES=[
        ("manual",      lambda car: 1 if car.get("is_manual") else 0),
        ("modified",    lambda car: 1 if car.get("is_modified") else 0),
        ("project",     lambda car: 1 if car.get("is_project") else 0),
        ("grade_project",lambda car: 1 if car.get("condition_grade")=="project" else 0),
        ("no_reserve",  lambda car: 1 if "no reserve" in (car.get("title") or "").lower() else 0),
        ("matching_eng",   lambda car: car.get("matching_engine")),
        ("matching_trans", lambda car: car.get("matching_trans")),
        ("service",     lambda car: car.get("recent_service")),
        ("rust",        lambda car: car.get("rust_mentioned")),
        #Coupe and unknown are baselines for body type
        ("cabriolet",   lambda car: 1 if car.get("body")=="cabriolet" else 0),
        ("targa",       lambda car: 1 if car.get("body")=="targa" else 0),
        ("sedan",       lambda car: 1 if car.get("body")=="sedan" else 0),
        ("roadster",    lambda car: 1 if car.get("body")=="roadster" else 0),
    ]

    centered={}
    means={}
    oks={}
    for feature_name,read_value in BINARY_FEATURES:
        values=[read_value(car) for car in usable]
        centered[feature_name],means[feature_name],oks[feature_name]=binary_feature(values)


    colors_raw=[(car.get("color") or "").lower() for car in usable]
    color_counts=Counter(c for c in colors_raw if c)
    #only top colors with >=15 examples get coefficient
    top_colors=[c for c,n in color_counts.most_common(6) if n>=15]
    color_arrays={}
    color_ok={}
    for c in top_colors:
        raw=[1 if x==c else 0 for x in colors_raw]
        color_ok[c]=usable_features(raw)
        arr=np.array(raw,dtype=float)
        if not color_ok[c]:
            arr=arr*0.0
        color_arrays[c]=arr

    variant_sets=[parsing.variants_info(car.get("title")) for car in usable]
    variant_counts=Counter()
    for s in variant_sets:
        for tok in s:
            variant_counts[tok]+=1
    top_variants=[v for v,n in variant_counts.most_common(10) if n>=15]
    variant_arrays={}
    variant_ok={}
    for v in top_variants:
        raw=[1 if v in s else 0 for s in variant_sets]
        variant_ok[v]=usable_features(raw)
        arr=np.array(raw,dtype=float)
        if not variant_ok[v]:
            arr=arr*0.0
        variant_arrays[v]=arr

    log_price=np.log(prices)

    #Make sale dates years since first sale to see market movement
    earliest=min(dates)
    sale_time=np.array([(d-earliest).days/365.0 for d in dates])
    sale_time_mean=sale_time.mean()
    sale_time_centered=sale_time-sale_time_mean

    #Avoid div by 0
    year_std=years.std()
    if year_std==0:
        year_std=1
    year_scaled=(years-years.mean())/year_std



    with pm.Model() as model:
        #Things model will learn
        intercept=pm.Normal("intercept",mu=log_price.mean(),sigma=2)
        b_year=pm.Normal("b_year",mu=0,sigma=1)
        b_mileage=pm.Normal("b_mileage",mu=0,sigma=1)
        b_gears=pm.Normal("b_gears",mu=0,sigma=1)
        b_condition=pm.Normal("b_condition",mu=0,sigma=1)
        b_score=pm.Normal("b_score",mu=0,sigma=1)
        b_major_flaws=pm.Normal("b_major_flaws",mu=0,sigma=1)
        b_time=pm.Normal("b_time",mu=0,sigma=1)
        noise=pm.HalfNormal("noise",sigma=1)

        b={}
        for feature_name,read_value in BINARY_FEATURES:
            if not oks[feature_name]:
                continue
            b[feature_name]=pm.Normal("b_"+feature_name,mu=0,sigma=1)
        binary_term=0
        for feature_name in b:
            binary_term=binary_term+b[feature_name]*centered[feature_name]

        b_colors={}
        for c in top_colors:
            if not color_ok[c]:
                continue
            name="b_color_"+c.replace(" ","_")
            b_colors[c]=pm.Normal(name,mu=0,sigma=1)
        color_term=0
        for c in b_colors:
            color_term=color_term+b_colors[c]*color_arrays[c]

        b_variants={}
        for v in top_variants:
            if not variant_ok[v]:
                continue
            name="b_var_"+v.replace(".","_").replace(" ","_")
            b_variants[v]=pm.Normal(name,mu=0,sigma=1)
        variant_term=0
        for v in b_variants:
            variant_term=variant_term+b_variants[v]*variant_arrays[v]

        #Model guess for car's log price
        guess=(intercept
               +binary_term
               +b_year*year_scaled
               +b_mileage*log_mileage_centered
               +b_gears*gears_centered
               +b_condition*condition_centered
               +b_score*score_centered
               +b_major_flaws*major_centered
               +color_term
               +variant_term
               +b_time*sale_time_centered)
        
        #Learns from real prices
        pm.StudentT("observed",nu=4,mu=guess,sigma=noise,observed=log_price)

        trace=pm.sample(1000,tune=1000,chains=4,cores=1,progressbar=True,random_seed=1)
        
    samples=trace.posterior

    def draws(name):
        #All sample values for one learned number in flat array
        return samples[name].values.flatten()
    
    def percent_effect(name,scale=1.0):
        middle=np.median(draws(name))
        return float(np.exp(middle*scale)-1)
    
    per_10k_scale=float(np.log((median_mileage+10000.0)/median_mileage))

    #What model predicts each feature is worth
    effects={
        #Standardize year and mileage to per 1 year newer, 10k miles more
        "per_year":percent_effect("b_year",1.0/year_std),
        "per_10k_miles":percent_effect("b_mileage",per_10k_scale) if mileage_ok else None,
        "per_gear":percent_effect("b_gears") if gears_ok  else None,
        "per_condition_step":percent_effect("b_condition") if cond_ok else None,
        "per_score_point":percent_effect("b_score") if score_ok else None,
        "per_major_flaw":percent_effect("b_major_flaws") if major_ok else None,
        "market_per_year":percent_effect("b_time"),
    }
    #Get all binary features into effects
    for feature_name,read_value in BINARY_FEATURES:
        effects[feature_name]=percent_effect("b_"+feature_name) if oks[feature_name] else None

    #Enter colors/variants that got through var guard
    for c in top_colors:
        name="b_color_"+c.replace(" ","_")
        effects[f"color_{c}"]=percent_effect(name) if color_ok[c] else None
    for v in top_variants:
        name="b_var_"+v.replace(".","_").replace(" ","_")
        effects[f"variant_{v}"]=percent_effect(name) if variant_ok[v] else None                                                                                               

    if target_car is None:
        #If no target car, typical stock coupe 1 year from most recent sale
        target_time=(sale_time.max()+1.0)-sale_time_mean
        predicted_log=draws("intercept")+draws("b_time")*target_time
        describes="a typical stock coupe 1 year from latest sale"
        contributions=None
    
    else:
        #Specific car's value at today's date
        
        if target_car.get("year"):
            target_year=(target_car["year"]-years.mean())/year_std
        else:
            target_year=0.0

        if target_car.get("mileage") and mileage_ok:
            target_mileage=np.log(target_car["mileage"])-log_mileage_fill
        else:
            target_mileage=0.0

        if target_car.get("gears") and gears_ok:
            target_gears=target_car["gears"]-gears_mean
        else:
            target_gears=0.0

        target_grade=grade_map.get(target_car.get("condition_grade"))
        if target_grade is not None and cond_ok:
            target_condition=target_grade-cond_mean
        else:
            target_condition=0.0

        if target_car.get("condition_score") is not None and score_ok:
            target_score=float(target_car["condition_score"])-score_mean
        else:
            target_score=0.0

        if target_car.get("major_flaw_count") is not None and major_ok:
            target_major=float(target_car["major_flaw_count"])-major_mean
        else:
            target_major=0.0
        
        target_values={}
        target_term=0.0
        for feature_name,read_value in BINARY_FEATURES:
            if not oks[feature_name]:
                continue
            value=target_binary(read_value(target_car),means[feature_name],oks[feature_name])
            target_values[feature_name]=value
            target_term=target_term+draws("b_"+feature_name)*value


        target_color=(target_car.get("color") or "").lower()
        color_predicted=0.0
        for c in top_colors:
            if target_color==c and color_ok[c]:
                name="b_color_"+c.replace(" ","_")
                color_predicted=color_predicted+draws(name)

        target_variants=parsing.variants_info(target_car.get("title"))
        variant_predicted=0.0
        for v in top_variants:
            if v in target_variants and variant_ok[v]:
                name="b_var_"+v.replace(".","_").replace(" ","_")
                variant_predicted=variant_predicted+draws(name)

        #as_of lets backtest price car at real sale date
        if as_of is not None:
            when=as_of
        else:
            when=datetime.now()
        time_now=(when-earliest).days/365.0-sale_time_mean

        predicted_log=(draws("intercept")
                       +target_term
                       +draws("b_year")*target_year
                       +draws("b_mileage")*target_mileage
                       +draws("b_gears")*target_gears
                       +draws("b_condition")*target_condition
                       +draws("b_score")*target_score
                       +draws("b_major_flaws")*target_major
                       +color_predicted
                       +variant_predicted
                       +draws("b_time")*time_now)
        describes="this specific car"

        def contrib(name,value):
            return float(np.exp(np.median(draws(name))*value)-1)
        contributions={
        "year":contrib("b_year",target_year),
        "mileage":contrib("b_mileage",target_mileage),
        "gears":contrib("b_gears",target_gears),
        "condition":contrib("b_condition",target_condition),
        "score":contrib("b_score",target_score),
        "major_flaws":contrib("b_major_flaws",target_major),
        "market_time":contrib("b_time",time_now),
        }

        for feature_name in target_values:
            contributions[feature_name]=contrib("b_"+feature_name,target_values[feature_name])

        for c in top_colors:
            if target_color==c and color_ok[c]:
                name="b_color_"+c.replace(" ","_")
                contributions[f"color_{c}"]=contrib(name,1.0)

        for v in top_variants:
            if v in target_variants and variant_ok[v]:
                name="b_var_"+v.replace(".","_").replace(" ","_")
                contributions[f"variant_{v}"]=contrib(name,1.0)

    predicted_price=np.exp(predicted_log)

    rng=np.random.default_rng(1)
    tail_draws=rng.standard_t(df=4,size=predicted_log.shape)
    could_sell_for=np.exp(predicted_log+tail_draws*draws("noise"))

    return{
        "predicted":int(np.median(predicted_price)),
        "low":int(np.percentile(could_sell_for,5)),
        "high":int(np.percentile(could_sell_for,95)),
        "count":len(usable),
        "effects":effects,
        "describes":describes,
        "baseline":int(np.exp(np.median(draws("intercept")))),
        "contributions":contributions,
    }


        





