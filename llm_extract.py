#Uses Ollama Qwen model to read description
#Saves results so only parsed once per car

import requests
import json
import sqlite3

OLLAMA_URL="http://localhost:11434/api/generate"
MODEL="qwen2.5:7b"
CACHE_DB="listing_cache.db"

PROMPT="""You are extracting facts from a car auction description.
Read the text and return ONLY a JSON object with these exact fields:
-condition_grade: one of "concours", "excellent", "driver", "project"
-matching_engine: true or false (is the engine original)
-matching_trans: true or false (is the transmission original)
-rust_mentioned: true or false
-recent_service: true or false (major service/rebuild since 2016)
-notable_flaws: a list of short strings (empty list if none)
 
Return only the JSON, no other text.
 
Description:
{text}"""

def setup_cache():
    #Make table if not existing
    con=sqlite3.connect(CACHE_DB)
    con.execute("CREATE TABLE IF NOT EXISTS listings(url TEXT PRIMARY KEY, features TEXT)")
    con.commit()
    con.close()

def cache_get(url):
    #Saved features for url, or none if not parsed before
    con=sqlite3.connect(CACHE_DB)
    row=con.execute("SELECT features FROM listings WHERE url=?",(url,)).fetchone()
    con.close()
    if row:
        return json.loads(row[0])
    return None

def cache_put(url,features):
    #Save or overwrite url features
    con=sqlite3.connect(CACHE_DB)
    con.execute("INSERT OR REPLACE INTO listings(url,features) VALUES(?,?)",(url,json.dumps(features)))
    con.commit()
    con.close()

def ask_qwen(text):
    payload={
        "model":MODEL,
        "prompt":PROMPT.format(text=text),
        "format":"json",
        "stream":False,
        #Temperature:0 makes qwen repeat same answer as much as possible
        "options":{"temperature":0},
    }
    response=requests.post(OLLAMA_URL,json=payload,timeout=120)
    response.raise_for_status()
    #JSON is in response field
    answer=response.json()["response"]
    return json.loads(answer)

def extract_features(url,description,use_cache=True):
    #Get condition for one listing
    #Check cache first
    if use_cache:
        cached=cache_get(url)
        if cached is not None:
            return cached
        
    if not description:
        return {}
    
    try:
        features=ask_qwen(description)
    except requests.exceptions.RequestException as e:
        print(f" model call failed, ollama running?: {e}")
        return {}
    except (json.JSONDecodeError,KeyError) as e:
        print(f" model gave bad output, skipping: {e}")
        return {}
    
    #Make sure grade is in list
    allowed=["concours","excellent","driver","project"]
    if features.get("condition_grade") not in allowed:
        features.pop("condition_grade",None)

    if use_cache:
        cache_put(url,features)
    return features
