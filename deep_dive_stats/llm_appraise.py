import json
import math
import deep_dive_stats.llm_extract as llm_extract
import helper_programs.parsing as parsing

#comps to show model:
HOW_MANY=8
#per comp discription:
COMP_CHARS=700
#target description:
TARGET_CHARS=1800

PROMPT="""You are a car auction appraiser. Below are recent sales of very
similar cars, then the car being valued. Estimate what the car being valued
would sell for at auction.
 
Weigh the comparable sales first - they are real prices for real cars. Then
adjust for differences you can see in the writeups: condition, mileage,
originality, quality of any restoration, rust, mechanical problems,
documentation, and how the car presents. A car with a documented quality
restoration and no faults sells well above one that needs work, even when
the basic specs match.
 
Return ONLY a JSON object:
{{"estimate": <whole dollars>, "low": <whole dollars>, "high": <whole dollars>,
 "reasoning": "<one sentence>"}}
The low and high should be a range you would be surprised to see the car
sell outside of.
 
COMPARABLE SALES:
{comps}
 
CAR BEING VALUED:
{target}"""

def _miles(car):
    m=car.get("mileage")
    return m if (m is not None and m>0) else None

def distance(car,target,mileage_scale):
    #show how unlike the target this comp is
    #lower better
    d=0.0
    y1,y2=car.get("year"),target.get("year")
    if y1 is not None and y2 is not None:
        #3 years apart is 1 unit
        d+=((y1-y2)/3.0)**2
    m1,m2=_miles(car),_miles(target)
    if m1 is not None and m2 is not None:
        d+=((math.log(m1)-math.log(m2))/mileage_scale)**2
    else:
        #unknown mileage is small penalty
        d+=0.5
    #different trim is different car
    t1=car.get("variant_tokens")
    t2=target.get("variant_tokens")
    if t1 is not None and t2 is not None and (t1 or t2):
        overlap=len(t1&t2)/max(1,len(t1|t2))
        d+=(1-overlap)*4.0
    return d

def nearest(target,comps,how_many=HOW_MANY):
    known=[math.log(m) for m in (_miles(c) for c in comps) if m is not None]
    if len(known)>=5:
        spread=max(0.2,float(sum((x-sum(known)/len(known))**2 for x in known)/len(known))**0.5)
    else:
        spread=1.0
    target=dict(target)
    target["variant_tokens"]=parsing.variants_info(target.get("title"))
    scored=[]
    for c in comps:
        if not c.get("price"):
            continue
        c=dict(c)
        c["variant_tokens"]=parsing.variants_info(c.get("title"))
        scored.append((distance(c,target,spread),c))
    scored.sort(key=lambda pair:pair[0])
    return [c for _,c in scored[:how_many]]

def describe(car,chars,with_price):
    bits=[]
    if with_price and car.get("price"):
        bits.append(f"SOLD FOR ${car["price"]:,}")
    if car.get("sale_date"):
        bits.append(car["sale_date"].strftime("%b %Y"))
    bits.append((car.get("title") or "?")[:70])
    facts=[]
    if _miles(car):
        facts.append(f"{car["mileage"]:,} miles")
    if car.get("condition_score") is not None:
        facts.append(f" condition: {car["condition_score"]}/10")
    if car.get("condition_grade"):
        facts.append(str(car["condition_grade"]))
    if car.get("rust_mentioned"):
        facts.append("rust noted")
    if car.get("color"):
        facts.append(str(car["color"]))
    line=" | ".join(bits)
    if facts:
        line+="\n "+", ".join(facts)
    text=(car.get("description") or "").strip()
    if text:
        line+="\n "+text[:chars].replace("\n"," ")
    return line

def appraise(target_car,comps,how_many=HOW_MANY):
    #returns {"estimate","low","high","reasoning"} or None
    picks=nearest(target_car,comps,how_many)
    if len(picks)<3:
        return None
    comp_text="\n\n".join(f"[{i+1}]"+describe(c,COMP_CHARS,True) for i,c in enumerate(picks))
    target_text=describe(target_car,TARGET_CHARS,False)
    prompt=PROMPT.format(comps=comp_text,target=target_text)

    raw=llm_extract.ask_raw(prompt)
    if not raw:
        return None
    out=llm_extract.extract_json(raw)
    if not out:
        return None
    #skip if models return wrong format (# instead of char, vice versa)
    try:
        estimate=int(round(float(out.get("estimate"))))
    except (TypeError,ValueError):
        return None
    if estimate<=0:
        return None

    def money(key,fallback):
        try:
            v=int(round(float(out.get(key))))
            return v if v>0 else fallback
        except (TypeError,ValueError):
            return fallback

    low=money("low",int(estimate*0.7))
    high=money("high",int(estimate*1.4))
    if low>high:
        low,high=high,low
    return {"estimate":estimate,"low":low,"high":high,
            "reasoning":str(out.get("reasoning",""))[:200],
            "comps_used":len(picks)}



