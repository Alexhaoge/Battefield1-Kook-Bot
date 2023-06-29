import json
import requests
import bs4
import re
import sqlite3
import httpx
from asyncio import gather, create_task
from typing import Union

API_SITE = "https://api.gametools.network/"

def request_API(game, prop: str = 'stats', params: dict = {}) -> Union[dict, requests.Response]:
    url = API_SITE+f'{game}/{prop}'

    res = requests.get(url,params=params)
    if res.status_code == 200:
        return json.loads(res.text)
    else:
        return res


async def fetch_data(url,headers):
    async with httpx.AsyncClient() as client:
        response = await client.get(url=url,headers=headers,timeout=20)
        return response

async def process_top_n(game: str, headers: dict, retry: int = 3):
    next_url = f"https://battlefieldtracker.com/{game}"
    for i in range(retry):
        try:
            game_req = await fetch_data(next_url,headers)
            soup = bs4.BeautifulSoup(game_req.text, 'html.parser')

            me = soup.select_one('.player.active')
            game_stat = {s.select_one('.name').text:s.select_one('.value').text for s in me.select('.quick-stats .stat')}
            break
        except AttributeError:
            continue
        except httpx.TimeoutException:
            continue
        except httpx.ConnectError:
            return 'player not found'

    game_stat['Kills'] = int(game_stat['Kills'])
    game_stat['Deaths'] = int(game_stat['Deaths'])
    game_stat['kd'] = round(game_stat['Kills'] / game_stat['Deaths'] if game_stat['Deaths'] else game_stat['Kills'], 2)
    duration = re.findall('[0-9]+m|[0-9]s', me.select_one('.player-subline').text)
    if len(duration):
        duration_in_min = sum([int(d[0:-1]) if d[-1] == 'm' else int(d[0:-1]) / 60 for d in duration])
        game_stat['kpm'] = round(game_stat['Kills'] / duration_in_min if duration_in_min else game_stat['Kills'], 2)
        game_stat['duration'] = ''.join(duration)
    else:
        game_stat['duration'] = game_stat['kpm'] = 'N/A'

    detail_general_card = me.findChild(name='h4', string='General').parent.parent
    game_stat['headshot'] = 'N/A'
    headshot_name_tag = detail_general_card.findChild(class_='name', string='Headshots')
    if headshot_name_tag:
        game_stat['headshot'] = int(headshot_name_tag.find_previous_sibling(class_='value').contents[0])

    team = me.findParents(class_="team")[0].select_one('.card-heading .card-title').contents[0]
    if team == 'No Team':
        game_stat['result'] = '未结算'
    else:
        team_win = soup.select('.card.match-attributes .stat .value')[1].contents[0]
        game_stat['result'] = '胜利' if team == team_win else '落败'

    map_info = soup.select_one('.match-header .activity-details')
    game_stat['map'] = map_info.select_one('.map-name').contents[0][0:-1]
    game_stat['mode'] = map_info.select_one('.type').contents[0]
    game_stat['server'] = map_info.select_one('.map-name small').contents[0]
    game_stat['matchDate'] = map_info.select_one('.date').contents[0]

    return game_stat    


async def async_bftracker_recent(origin_id: str, top_n: int = 3) -> Union[list, str]:
    headers = {
        "Connection": "keep-alive",
        "User-Agent": "ProtoHttp 1.3/DS 15.1.2.1.0 (Windows)",
    }
    url=f'https://battlefieldtracker.com/bf1/profile/pc/{origin_id}/matches'

    games_req = await fetch_data(url,headers)
  
    soup = bs4.BeautifulSoup(games_req.text, 'html.parser')
    if soup.select('.alert.alert-danger.alert-dismissable'):
        return 'player not found'
    games = soup.select('.bf1-profile .profile-main .content .matches a')[:top_n]
    tasks = []
    for i in range(top_n):
        tasks.append(create_task(process_top_n(games[i]['href'], headers)))
    
    results = await gather(*tasks, return_exceptions=True)
    return results


def verify_originid(origin_id: str) -> bool:
    result = request_API('bf1', 'player', {'name': origin_id})
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            return False
    return True


def db_op(con: sqlite3.Connection, sql: str):
    cur = con.cursor()
    res = con.execute(sql).fetchall()
    cur.connection.commit()
    cur.close()
    return res    
