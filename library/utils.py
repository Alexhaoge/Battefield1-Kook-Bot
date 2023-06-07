import json
import requests
from typing import Union

API_SITE = "https://api.gametools.network/"

def request_API(game, prop='stats', params={}) -> Union[dict, requests.Response]:
    url = API_SITE+f'{game}/{prop}'

    res = requests.get(url,params=params)
    if res.status_code == 200:
        return json.loads(res.text)
    else:
        return res