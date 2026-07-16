#Uses Ollama Qwen model to read description
#Saves results so only parsed once per car

import requests
import json

OLLAMA_URL="http://localhost:11434/api/generate"
MODEL="qwen2.5:3b"
CACHE_DB="listing_cache.db"

PROMPT="""You are extracting facts from a car auction description.
Read the text and return ONLY a JSON object with these exact fields:
-condition_grade: exactly one of "project","driver","excellent","concours"
  "project": the car currently does not run or drive, OR the text says it
   NEEDS major mechanical or body work
  "driver": runs and drives, honest wear, an ordinary used example
  "excellent": genuinely outstanding example, only minor flaws mentioned
  "concours": show quality, restored or kept to a very high standard
  RULES for condition_grade:
  -Work that was ALREADY done (service, repairs, parts, restoration)
   counts in the car's FAVOR. A long list of completed repairs does NOT
   make a car a "project".
  -Only grade "project" if the car does not run or drive now, or still
   NEEDS major work. If it runs and drives, it is "driver" or better.
  -Small flaws (trim, one window, paint chips, missing cupholder) belong
   in notable_flaws and do NOT make a car a "project".
   -Modifications do NOT make a car a "project", but they do decrease the grade if they are not tasteful or high quality
  Most cars are "driver", but not all cars. Cars can be projects, excellent, and some are concours. Use your best judgment.
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
    response=requests.post(OLLAMA_URL,json=payload,timeout=600)
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
    