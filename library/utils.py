import re
# import sqlite3
import aiosqlite
import httpx
import uuid
from io import BytesIO
from matplotlib.figure import Figure
from matplotlib.pyplot import savefig
from typing import Union, List, Tuple
from khl import User, Bot
from .util_dict import STR_SIMP, STR_TRAD

API_SITE = "https://api.gametools.network/"

def request_API(game, prop: str = 'stats', params: dict = {}) -> Union[dict, httpx.Response]:
    url = API_SITE+f'{game}/{prop}'
    res = httpx.get(url,params=params)
    if res.status_code == 200:
        return res.json()
    else:
        return res

async def fetch_data(url,headers):
    async with httpx.AsyncClient() as client:
        response = await client.get(url=url,headers=headers,timeout=20)
        return response

async def async_request_API(game, prop: str = 'stats', params: dict = {}) -> Union[dict, httpx.Response]:
    async with httpx.AsyncClient() as client:
        res = await client.get(url=f'{API_SITE}{game}/{prop}',params=params, timeout=20)
        if res.status_code == 200:
            return res.json()
        else:
            return res

def verify_originid(origin_id: str) -> Union[bool, str]:
    result = request_API('bf1', 'player', {'name': origin_id})
    if isinstance(result, httpx.Response):
        return False
    return result['userName']

def upd_remid_sid(res: httpx.Response, remid, sid) -> Tuple[str, str]:
    res_cookies = res.cookies
    if 'sid' in res_cookies:
        sid = res_cookies['sid']
    if 'remid' in res_cookies:
        remid = res_cookies['remid']
    return remid, sid

def upd_sessionID(remid: str, sid: str) -> Tuple[str, str, str]:
    res_access_token = httpx.get(
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

    res_authcode = httpx.get(
        url="https://accounts.ea.com/connect/auth",
        params= {
            'client_id': 'sparta-backend-as-user-pc',
            'response_type': 'code',    'release_type': 'none'
        },
        headers= {'Cookie': f'remid={remid};sid={sid}'},
        follow_redirects=False
    )
    authcode = str.split(res_authcode.next_request.url.query.decode(), "=")[1]
    remid, sid = upd_remid_sid(res_authcode, remid, sid)

    res_session = httpx.post(
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

# def db_op(conn: sqlite3.Connection, sql: str, params: list):
#     cur = conn.cursor()
#     res = conn.execute(sql, params).fetchall()
#     conn.commit()
#     cur.close()
#     return res    

async def async_db_op(conn: str, sql: str, params: list):
    db = await aiosqlite.connect(conn)
    cursor = await db.execute(sql, params)
    res = await cursor.fetchall()
    await db.commit()
    await cursor.close()
    await db.close()
    return res    

async def async_db_op_exe_many(conn: str, sql: str, params: list):
    db = await aiosqlite.connect(conn)
    cursor = await db.executemany(sql, params)
    await db.commit()
    await cursor.close()
    await db.close()

async def check_owner_perm(con: str, author: User, group: str, super_admin: list) -> bool:
    if author.username.lower()  + '#' + author.identify_num in super_admin:
        return True
    res = await async_db_op(con, "SELECT owner FROM server_groups WHERE name=?;", [group]).fetchall()
    return res[0][0] == author.id

async def check_admin_perm(con: str, author: User, group: str, super_admin: list) -> bool:
    if author.username.lower()  + '#' + author.identify_num in super_admin:
        return True
    res = await async_db_op(con, "SELECT id FROM server_admins WHERE id=? AND group=?;", [author.id, group]).fetchall()
    return len(res) > 0

def split_kook_name(name: str) -> Union[List[str], bool]:
    if re.match('\w+#[0-9]+', name):
        return [s.lower() for s in name.split('#', 1)]
    else:
        return False

async def check_server_by_db(con: str, group: str, group_num: int) -> Union[Tuple, bool]:
    """
    Check if the given server nickname exists in the database. Return (gameId, persistedGameId) if the server exists, otherwise return boolean false.
    """
    existing_server = await async_db_op(con, "SELECT gameid, serverid FROM servers WHERE `group`=? AND group_num=?;", [group, group_num])
    return existing_server[0] if len(existing_server) else False


class RSPException(Exception):
    code_dict = {
        -32856: "玩家ID有误",
        -32851: "服务器已过期或不存在",
        -32857: "机器人无法处置管理员",
        -35150: "战队不存在",
        -32504: "EA服务器访问超时",
        -34501: "服务器已过期或不存在",
        -32602: "参数缺失"
    }

    def __init__(self, msg: str = None, error_code: int = None):
        self.msg = msg
        self.code = error_code
    
    def __str__(self):
        return f"{self.code}:{self.msg}"
    
    def echo(self, admin_originid: str = None, admin_personaid: int = None):
        if self.code in RSPException.code_dict.keys():
            return RSPException.code_dict[self.code]
        else:
            msg_lower = self.msg.lower()
            if "session expired" in msg_lower or "no varlid session" in msg_lower:
                return f"{admin_originid}({admin_personaid})的SessionID失效，请联系管理员刷新"
            elif "severnotrestartableexception" in msg_lower:
                return "服务器未开启"
            elif "org.apache.thrift.tapplicationexception" in msg_lower:
                return "机器人无权限操作"
            elif "rsperruserisalreadyvip" in msg_lower:
                return "玩家已是vip"
            elif "rsperrservervipmax" in msg_lower:
                return "服务器VIP位已满"
            elif "rsperrserverbanmax" in msg_lower:
                return "服务器Ban位已满"
            elif "rsperrinvalidmaprotationid" in msg_lower:
                return "无效地图轮换"
            elif "invalidlevelindexexception" in msg_lower:
                return "图池索引错误"
            elif "invalidserveridexception" in msg_lower:
                return "服务器ServerId错误"
            else:
                return f"未知错误{self.__str__()}"


def rsp_API(method_name: str, params: dict, sessionID: str) -> dict:
    params["game"] = "tunguska"
    res = httpx.post(
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
        raise RSPException(res_json['error']['message'], res_json['error']['code'])
    return res_json

async def async_rsp_API(method_name: str, params: dict, sessionID: str) -> dict: 
    params["game"] = "tunguska"
    async with httpx.AsyncClient() as client:
        res = await client.post(
            url="https://sparta-gw.battlelog.com/jsonrpc/pc/api",
            json= {
                'jsonrpc': '2.0',
                'method': method_name,
                'params': params,
                "id": str(uuid.uuid4())
            },
            headers= { 'X-GatewaySession': sessionID },
            timeout=20
        )
        res_json = res.json()
        if 'error' in res_json:
            raise RSPException(res_json['error']['message'], res_json['error']['code'])
        return res_json


def zh_simp_to_trad(str:str):
    str1 = ''
    for i in str:
        j = STR_SIMP.find(i)
        if j == -1:
            str1 = str1 + i
        else:
            str1 = str1 + STR_TRAD[j]
    return str1

def zh_trad_to_simp(str:str):
    str1 = ''
    for i in str:
        j = STR_TRAD.find(i)
        if j == -1:
            str1 = str1 + i
        else:
            str1 = str1 + STR_SIMP[j]
    return str1

async def fig_to_kook_asset(fig: Figure, bot: Bot):
    img_byte = BytesIO()
    savefig(img_byte, format='png')
    img_url = await bot.client.create_asset(BytesIO(img_byte.getvalue()))
    return img_url