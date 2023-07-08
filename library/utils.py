import requests
import bs4
import re
import sqlite3
import httpx
import uuid
from asyncio import gather, create_task
from typing import Union, List, Tuple
from khl import User
from .util_dict import STR_SIMP, STR_TRAD

API_SITE = "https://api.gametools.network/"

def request_API(game, prop: str = 'stats', params: dict = {}) -> Union[dict, requests.Response]:
    url = API_SITE+f'{game}/{prop}'
    res = requests.get(url,params=params)
    if res.status_code == 200:
        return res.json()
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
    duration = re.findall('[0-9]+m|[0-9]+s', me.select_one('.player-subline').text)
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


def verify_originid(origin_id: str) -> Union[bool, str]:
    result = request_API('bf1', 'player', {'name': origin_id})
    if isinstance(result, requests.Response):
        return False
    return result['userName']

def upd_remid_sid(res: requests.Response, remid, sid) -> Tuple[str, str]:
    res_cookies = requests.utils.dict_from_cookiejar(res.cookies)
    if 'sid' in res_cookies:
        sid = res_cookies['sid']
    if 'remid' in res_cookies:
        remid = res_cookies['remid']
    return remid, sid

def upd_sessionID(remid: str, sid: str) -> Tuple[str, str, str]:
    res_access_token = requests.get(
        url="https://accounts.ea.com/connect/auth",
        params= {
            'client_id': 'ORIGIN_JS_SDK',   'response_type': 'token',
            'redirect_uri': 'nucleus:rest', 'prompt': 'none',   'release_type': 'prod'
        },
        headers= {
            'Cookie': f'remid={remid};sid={sid}',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.193 Safari/537.36',
            'content-type': 'application/json'
        }
    )
    if 'access_token' not in res_access_token.json():
        raise Exception('cookie expired')
    remid, sid = upd_remid_sid(res_access_token, remid, sid)

    res_authcode = requests.get(
        url="https://accounts.ea.com/connect/auth",
        params= {
            'client_id': 'sparta-backend-as-user-pc',
            'response_type': 'code',    'release_type': 'none'
        },
        headers= {'Cookie': f'remid={remid};sid={sid}'},
        allow_redirects=False
    )
    authcode = str.split(res_authcode.next.path_url, "=")[1]
    remid, sid = upd_remid_sid(res_authcode, remid, sid)

    res_session = requests.post(
        url="https://sparta-gw.battlelog.com/jsonrpc/pc/api",
        json= {
            'jsonrpc': '2.0',
            'method': 'Authentication.getEnvIdViaAuthCode',
            'params': {
                'authCode': authcode
            },
            "id": str(uuid.uuid4())
        }
    )
    sessionID = res_session.json()['result']['sessionId']
    return remid, sid, sessionID    


def db_op(con: sqlite3.Connection, sql: str, params: list):
    cur = con.cursor()
    res = con.execute(sql, params).fetchall()
    cur.connection.commit()
    cur.close()
    return res    

def check_owner_perm(con: sqlite3.Connection, author: User, group: str, super_admin: list) -> bool:
    if author.username.lower()  + '#' + author.identify_num in super_admin:
        return True
    res = db_op(con, "SELECT owner FROM server_groups WHERE name=?;", [group]).fetchall()
    return res[0][0] == author.id

def check_admin_perm(con: sqlite3.Connection, author: User, group: str, super_admin: list) -> bool:
    if author.username.lower()  + '#' + author.identify_num in super_admin:
        return True
    res = db_op(con, "SELECT id FROM server_admins WHERE id=? AND group=?;", [author.id, group]).fetchall()
    return len(res) > 0

def split_kook_name(name: str) -> Union[List[str], bool]:
    if re.match('\w+#[0-9]+', name):
        return [s.lower() for s in name.split('#', 1)]
    else:
        return False

def check_server_by_db(con: sqlite3.Connection, group: str, group_num: int) -> Union[Tuple, bool]:
    """
    Check if the given server nickname exists in the database. Return (gameid, serverid) if the server exists, otherwise return boolean false.
    """
    existing_server = db_op(con, "SELECT gameid, serverid FROM servers WHERE `group`=? AND group_num=?;", [group, group_num])
    return existing_server[0] if len(existing_server) else False


class SessionIdError(Exception):
    def __init__(self, msg: str = None, status_code: int = None):
        self.msg = msg
        self.status_code = status_code
    
    def __str__(self):
        return f"{self.status_code}:{self.msg}"

def rsp_API(method_name: str, params: dict, sessionID: str) -> Union[dict, requests.HTTPError]: 
    params["game"] = "tunguska"
    res = requests.post(
        url="https://sparta-gw.battlelog.com/jsonrpc/pc/api",
        json= {
            'jsonrpc': '2.0',
            'method': method_name,
            'params': params,
            "id": str(uuid.uuid4())
        },
        headers= { 'X-GatewaySession': sessionID },
    )
    res_json = res.json()
    if 'error' in res_json:
        raise SessionIdError(res_json['error']['message'], res.status_code)
    return res_json


def zhconvert(str:str):
    str1 = ''
    for i in str:
        j = STR_SIMP.find(i)
        if j == -1:
            str1 = str1 + i
        else:
            str1 = str1 + STR_TRAD[j]
    return str1