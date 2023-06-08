import json
import requests
import bs4
from typing import Union

API_SITE = "https://api.gametools.network/"

def request_API(game, prop='stats', params={}) -> Union[dict, requests.Response]:
    url = API_SITE+f'{game}/{prop}'

    res = requests.get(url,params=params)
    if res.status_code == 200:
        return json.loads(res.text)
    else:
        return res
    
def bftracker_recent(origin_id: str, top_n: int = 3) -> Union[list, str]:
    headers = {
        "Connection": "keep-alive",
        "User-Agent": "ProtoHttp 1.3/DS 15.1.2.1.0 (Windows)",
    }
    games_req = requests.get(
        url=f'https://battlefieldtracker.com/bf1/profile/pc/{origin_id}/matches',
        headers=headers
    )
    soup = bs4.BeautifulSoup(games_req.text, 'html.parser')
    if soup.select('.alert.alert-danger.alert-dismissable'):
        return 'player not found'
    games = soup.select('.bf1-profile .profile-main .content .matches a')[:top_n]
    games_dat = []
    for i in range(top_n):
        next_url = f"https://battlefieldtracker.com/{games[i]['href']}"
        game_req = requests.get(url=next_url, headers=headers)
        soup = bs4.BeautifulSoup(game_req.text, 'html.parser')

        me = soup.select_one('.player.active')
        game_stat = {s.select_one('.name').text:s.select_one('.value').text for s in me.select('.quick-stats .stat')}
        
        team = me.findParents(class_="team")[0].select_one('.card-heading .card-title').contents[0]
        if team == 'No Team':
            game_stat['result'] = '未结算'
        else:
            team_win = soup.select('.card.match-attributes .stat .name')[1].find_previous_sibling(class_='value').contents[0]
            game_stat['result'] = '胜利' if team == team_win else '落败'
        
        map_info = soup.select_one('.match-header .activity-details')
        game_stat['map'] = map_info.select_one('.map-name').contents[0]
        game_stat['mode'] = map_info.select_one('.type').contents[0]
        game_stat['server'] = map_info.select_one('.map-name small').contents[0]

        games_dat.append(game_stat)
    
    return games_dat