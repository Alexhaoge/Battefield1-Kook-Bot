import json
import requests

API_SITE = "https://api.gametools.network/"

def request_API(game, prop='stats', params={}):
    url = API_SITE+f'{game}/{prop}'

    res = requests.get(url,params=params)
    if res.status_code == 200:
        return json.loads(res.text)
    else:
        raise requests.HTTPError