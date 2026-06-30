#Simple estimates of prices used in live tracking
from datetime import datetime

def trimmed_mean(prices,trim_percent=5):
    prices=sorted(prices)

    if len(prices)<=5:
        return sum(prices)//len(prices)
    
    #Cut top and bottom trim_percent of prices to trim outliers
    cut=len(prices)*trim_percent//100
    if cut<1:
        cut=1
    
    kept=prices[cut:-cut]
    return sum(kept)//len(kept)

def recent_average(cars):
    #Average of sales from last 2 years
    now=datetime.now
    recent_prices=[]

    for car in cars:
        date=car["sale_date"]
        if date is None:
            continue
        days_old=(now-date).days
        #Keep last 2 years
        if days_old<=730:
            recent_prices.append(car["price"])

    if len(recent_prices)==0:
        return None
    return sum(recent_prices)//len(recent_prices)
    
def estimate_price(cars):
    #Need sufficient sample size
    if len(cars)<3:
        return None
    
    prices=[car["price"] for car in cars]
    
    summary={
        "average":trimmed_mean(prices),
        "recent":recent_average(cars),
        "low":min(prices),
        "high":max(prices),
        "count":len(prices),
    }
    return summary

def deal_label(current_bid,estimate,threshold):
    if estimate is None:
        return "no data"
    
    average=estimate["average"]
    percent=(current_bid-average)/average*100
    
    if percent<-threshold:
        verdict="GOOD"
    elif percent>threshold:
        verdict="BAD"
    else:
        verdict="FAIR"

    if percent<0:
        direction="BELOW"
    else:
        direction="ABOVE"

    return print(f"{verdict} {abs(round(percent))}% {direction} avg (${average:,}, n={estimate["count"]})")
