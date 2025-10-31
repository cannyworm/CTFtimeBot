import json


def load_config():
    try :
        with open("config.json","r") as f :
            return json.load(f)
    except FileNotFoundError :
        return {}

def save_config(data) :
    with open("config.json","w") as f:
        json.dump(data,f,indent=4)


def load_subscribe():
    try :
        with open("subscribe.json","r") as f :
            return json.load(f)
    except FileNotFoundError :
        return {}

def save_subscribe(data):
    with open("subscribe.json","w") as f :
        json.dump(data,f,indent=4)
