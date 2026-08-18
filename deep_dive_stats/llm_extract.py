#Uses Ollama LLM model to read description
#Saves results so only parsed once per car

import requests
import json

OLLAMA_URL="http://localhost:11434/api/generate"
MODEL="gpt-oss:20b"
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
   in minor_flaws and do NOT make a car a "project".
   -Modifications do NOT make a car a "project", but they do decrease the grade if they are not tasteful or high quality
  Most cars are "driver", but not all cars. Cars can be projects, excellent, and some are concours. Use your best judgment.
-recent_service: true if a major service, rebuild, or significant mechanical
 work has been done since 2016. false if the description covers the car's
 history and no such major work appears. Use null only if the description says
 nothing about maintenance. Minor repairs and upkeep do not make this true
-matching_engine: true if the engine is the original one the car left the
 factory with, false if it is a replacement or from another car. A rebuilt
 engine is still original - rebuilding does not make it false. If the
 description does not say, use null.
-matching_trans: true if the transmission is the original one the car left the
 factory with, false if it is a replacement or from another car. A rebuilt
 transmission is still original - rebuilding does not make it false. If the
 description does not say, use null.
-rust_mentioned: true if the description mentions CURRENT rust, bubbling, blistering,
 paint lifting on arches, sills, rockers or floors, or past rust repair or
 replaced metal. false if the description covers the body, paint, or
 underside and none of those appear - most cars are false. Use null only if
 the description says nothing at all about the body or paint. 
 If it mentions repaired rust, it will be false. Do not count historical rust against the car.
-major_flaws: a list of short strings for problems that would meaningfully
 affect value - rust, accident damage, mechanical faults, non-running
 systems, failed paint
-minor_flaws: a list of short strings for cosmetic or trivial items -
 small chips, worn trim, a squeaky belt, an inoperative clock
-condition_score: an integer 1-10. 1 is a shell or parts car, 3 is a
 non-running project, 5 is an ordinary driver with honest wear, 7 is a very
 good car with only cosmetic flaws, 9 is a fresh high-quality restoration,
 10 is concours. The two condition fields must agree: "project" is 1-3,
 "driver" is 4-6, "excellent" is 7-8, "concours" is 9-10. Many major flaws, such as
 Currently documented rust, leaks, or non-working systems pull the score below 5; a car with several is
 a 3 or 4. Minor cosmetic issues pull it down slightly, maybe not at all if they are very minor. Completed quality
 work pulls score up. Restorations in good quality will pull score up. A car can be 9 or 10 even if the description does not state concours.
 Make judgement of grade based on the honest shape the car CURRENTLY is in.
 Do not default to 5 or 6 - decide from the flaws you listed above.

Return only the JSON, no other text.

Description:
{text}"""

def extract_json(text):
    #Reasoning models can put text around answer, so only extract whats wanted
    start=text.find("{")
    end=text.rfind("}")
    if start==-1 or end==-1 or end<start:
        return None
    try:
        return json.loads(text[start:end+1])
    except json.JSONDecodeError:
        return None
    
def ask_llm(text):
    payload={"model":MODEL,
        "messages":[{"role":"user","content":PROMPT.format(text=text)}],
        "stream":False,"think":"low",
        "options":{"temperature":0,"num_ctx":8192},
        "keep_alive":"30m"}
    response=requests.post("http://localhost:11434/api/chat",json=payload,timeout=600)
    response.raise_for_status()
    return extract_json(response.json()["message"]["content"])

def parse_condition(description):
    #Run description through llm
    #Return condition info
    try:
        feats=ask_llm(description)
        if not feats:
            print("Model gave no JSON, skipping")
            return {}
    except requests.exceptions.RequestException as e:
        print(f" model call failed, ollama running?: {e}")
        return {}
    except (json.JSONDecodeError,KeyError) as e:
        print(f" model gave bad output, skipping: {e}")
        return {}
    
    allowed=["concours","excellent","driver","project"]
    if feats.get("condition_grade") not in allowed:
        feats.pop("condition_grade",None)

    for key in ("major_flaws","minor_flaws"):
        if not isinstance(feats.get(key),list):
            feats[key]=[]
    score=feats.get("condition_score")
    try:
        score=int(score)
    except (TypeError,ValueError):
        score=None
    if score is not None and not 1<=score<=10:
        score=None
    feats["condition_score"]=score
    return feats
    