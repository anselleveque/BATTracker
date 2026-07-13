#Every sale saved 
#Quick description and in-depth
#In-depth fills a few at a time

import sqlite3
import json

DB="sales.db"

def setup():
    #Make table
    #URL primary key
    con=sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS sales(
                url TEXT PRIMARY KEY,
                title TEXT,
                price INTEGER,
                year INTEGER,
                sale_date TEXT,
                mileage INTEGER,
                body TEXT,
                is_manual INTEGER,
                gears INTEGER,
                engine TEXT,
                model TEXT,
                sold INTEGER,
                description TEXT,
                chassis TEXT,
                is_modified INTEGER,
                is_project INTEGER,
                condition_grade TEXT,
                matching_engine INTEGER,
                matching_trans INTEGER,
                rust_mentioned INTEGER,
                recent_service INTEGER,
                notable_flaws TEXT,
                enriched INTEGER DEFAULT 0
            )""")
    con.commit()
    con.close()

def save_comps(cars):
    #Save basics of comps
    con=sqlite3.connect(DB)
    for car in cars:
        if car.get("sale_date") is not None:
            date_text=car["sale_date"].strftime("%Y-%m-%d")
        else:
            date_text=""
        con.execute("""INSERT OR IGNORE INTO sales
                    (url,title,price,year,mileage,sale_date,body,is_manual,gears,engine,
                    is_modified,is_project,sold,enriched)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,0)""",
            (car.get("url"),car.get("title"),car.get("price"),car.get("year"),car.get("mileage"),
             date_text,car.get("body"),
             int(bool(car.get("is_manual"))),car.get("gears"),car.get("engine"),
             int(bool(car.get("is_modified"))),int(bool(car.get("is_project"))),to_int_or_none(car.get("sold"))))
    con.commit()
    con.close()

def load_comps(search_words,year_from=None,year_to=None,model=None,max_age_years=None):
    #Read matching sales from databse
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    rows=con.execute("SELECT*FROM sales").fetchall()
    con.close()

    from datetime import datetime
    comps=[]
    for row in rows:
        #skip auctions that didn't sell
        if row["sold"] is not None and row["sold"]==0:
            continue

        if model is not None and row["model"] is not None:
            if row["model"].lower()!=model.lower():
                continue
        else:
            title=(row["title"] or "").lower()
            if not all(word in title for word in search_words):
                continue

        if year_from is not None and row["year"] is not None and row["year"]<year_from:
            continue
        if year_to is not None and row["year"] is not None and row["year"]>year_to:
            continue

        #Rebuild car dict
        if row["sale_date"]:
            date=datetime.strptime(row["sale_date"],"%Y-%m-%d")
        else:
            date=None

        if max_age_years is not None:
            if date is None or (datetime.now()-date).days/365.0>max_age_years:
                continue
            
        comps.append({
            "url":row["url"],
            "title":row["title"],
            "model":row["model"],
            "price":row["price"],
            "year":row["year"],
            "mileage":row["mileage"],
            "sale_date":date,
            "body":row["body"],
            "is_manual":bool(row["is_manual"]),
            "gears":row["gears"],
            "engine":row["engine"],
            "chassis":row["chassis"],
            "is_modified":bool(row["is_modified"]),
            "is_project":bool(row["is_project"]),
            "condition_grade":row["condition_grade"],
            "matching_engine":row["matching_engine"],
            "matching_trans":row["matching_trans"],
            "rust_mentioned":row["rust_mentioned"],
            "recent_service":row["recent_service"],
            "flaw_count":count_flaws(row["notable_flaws"])
        })

    #Keep only newest sale per chassis
    newest={}
    no_chassis=[]
    for car in comps:
        ch=car.get("chassis")
        if not ch:
            no_chassis.append(car)
        elif ch not in newest:
            newest[ch]=car
        elif car.get("sale_date") and newest[ch].get("sale_date") and car["sale_date"]>newest[ch]["sale_date"]:
            newest[ch]=car
    comps=no_chassis+list(newest.values())

    return comps

def get_condition(url):
    #Return condition for sale
    #If not none, skip parsing condition again
    con=sqlite3.connect(DB)
    con.row_factory=sqlite3.Row
    row=con.execute("SELECT * FROM sales WHERE url=? AND enriched=1",(url,)).fetchone()
    con.close()
    if row is None:
        return None
    return{
        "condition_grade":row["condition_grade"],
        "matching_engine":row["matching_engine"],
        "matching_trans":row["matching_trans"],
        "rust_mentioned":row["rust_mentioned"],
        "recent_service":row["recent_service"],
        "flaw_count":count_flaws(row["notable_flaws"]),
        "model":row["model"],
    }

def needs_enrichment(limit):
    #Return up to limit saved urls that have unfetched conditio
    con=sqlite3.connect(DB)
    rows=con.execute("SELECT url FROM sales WHERE enriched=0 LIMIT ?",(limit,)).fetchall()
    con.close()
    return [row[0] for row in rows]

def save_condition(url,features,model=None,description=None,chassis=None):
    #Get condition fields and mark enriched
    if chassis:
        chassis=chassis.strip().upper()
    con=sqlite3.connect(DB)
    con.execute("INSERT OR IGNORE INTO sales(url,enriched) VALUES(?,0)",(url,))
    flaws=json.dumps(features.get("notable_flaws",[]))
    con.execute("""UPDATE sales SET
                condition_grade=?,matching_engine=?,matching_trans=?,
                rust_mentioned=?, recent_service=?,notable_flaws=?,
                model=?,description=?,chassis=?,enriched=1
                WHERE url=?""",
                (features.get("condition_grade"),
                to_int_or_none(features.get("matching_engine")),
                to_int_or_none(features.get("matching_trans")),
                to_int_or_none(features.get("rust_mentioned")),
                to_int_or_none(features.get("recent_service")),
                flaws,model,description,chassis,url))
    con.commit()
    con.close()

def to_int_or_none(value):
    if value is None:
        return None
    return int(bool(value))

def count_flaws(flaws_text):
    #Count num of flaws
    #If None, model not parsed,!=0 flaws
    if flaws_text is None:
        return None
    try:
        return len(json.loads(flaws_text))
    except json.JSONDecodeError:
        return None

def stats():
    con=sqlite3.connect(DB)
    total=con.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
    enriched=con.execute("SELECT COUNT(*) FROM sales WHERE enriched=1").fetchone()[0]
    con.close()
    return total,enriched

def clear_database():
    #CLEARS ALL RECORDS FROM DB
    #USE CAREFULLY
    con=sqlite3.connect(DB)
    con.execute("DELETE FROM sales")
    con.commit()
    con.close()
    print("Database cleared")


