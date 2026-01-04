import json, time
# create old format file: chat id -> single list of 6 numbers
data = {"12345": [80,45,40,6.5,60,30], "67890": [[{"id":1,"label":"plot1","values":[70,35,30,6.2,55,28],"ts": 0}]]}
with open('user_soil.json','w',encoding='utf-8') as f:
    json.dump(data,f,indent=2)

# Now run a tiny normalization similar to main.load_user_soil
with open('user_soil.json','r',encoding='utf-8') as f:
    raw = json.load(f)

normalized = {}
for chat_id_str, val in raw.items():
    chat_id = int(chat_id_str)
    if isinstance(val, list) and len(val) == 6 and (not val or isinstance(val[0], (int, float))):
        normalized[chat_id] = [{"id": 1, "label": None, "values": val, "ts": time.time()}]
    elif isinstance(val, list):
        normalized[chat_id] = val
    else:
        normalized[chat_id] = []

print('Normalized:')
print(json.dumps({str(k): v for k,v in normalized.items()}, indent=2))
