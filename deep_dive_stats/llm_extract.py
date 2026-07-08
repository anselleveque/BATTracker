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

def parse_condition(description):
    #Run description through Qwen
    #Return condition info
    try:
        feats=ask_qwen(description)
    except requests.exceptions.RequestException as e:
        print(f" model call failed, ollama running?: {e}")
        return {}
    except (json.JSONDecodeError,KeyError) as e:
        print(f" model gave bad output, skipping: {e}")
        return {}
    
    allowed=["concours","excellent","driver","project"]
    if feats.get("condition_grade") not in allowed:
        feats.pop("condition_grade",None)
    return feats
    