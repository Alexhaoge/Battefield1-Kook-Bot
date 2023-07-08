import logging
import sqlite3
import requests
import atexit

from khl import Bot, Message
from secret import token, super_admin
from random import choice

from library.utils import (
    request_API, async_bftracker_recent,
    upd_sessionID, db_op, verify_originid, zhconvert,
    check_owner_perm, split_kook_name,
    check_admin_perm, check_server_by_db, rsp_API, SessionIdError
)
from library.cardTemplate import (
    render_stat_card, render_find_server_card, render_recent_card
)
from library.util_dict import map_zh_dict, zh_team_name_by_key

bot = Bot(token=token)

conn = sqlite3.connect('bot.db')
def close_db():
    conn.close()

hello_messages = ['你好！', 'Hello!', 'Bonjour!', 'Hola!', 'Ciao!', 'Hallo!', 'こんにちは!']
@bot.command(name='hello')
async def world(msg: Message):
    """
    /hello return welcome message
    """
    await msg.reply(choice(hello_messages))

@bot.command(name='stat')
async def bf1_player_stat(msg: Message, origin_id: str = None):
    """
    /stat originid
    """
    if origin_id is None:
        user = db_op(conn, "SELECT originid FROM players WHERE id=?;", [msg.author.id])
        if len(user):
            origin_id = user[0][0]
        else:
            await msg.reply(f'未绑定账号')
            return
    result = request_API('bf1','all',{'name':origin_id, 'lang':'zh-tw'})
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            logging.info(f'BF1 User {origin_id} not found')
        await msg.reply(f'玩家{origin_id}不存在')
        return
    await msg.reply(render_stat_card(result))

@bot.command(name='f')
async def bf1_find_server(msg: Message, server_name: str):
    result = request_API('bf1', 'servers', {'name': server_name, 'lang':'zh-tw'})
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            logging.info(f'error getting server info')
        await msg.reply(f'找不到任何相关服务器')
        return
    await msg.reply(render_find_server_card(result))

@bot.command(name='r')
async def bf1_recent(msg: Message, origin_id: str = None):
    if origin_id is None:
        user = db_op(conn, "SELECT originid FROM players WHERE id=?;", [msg.author.id])
        if len(user):
            origin_id = user[0][0]
        else:
            await msg.reply(f'未绑定账号')
            return
    result = await async_bftracker_recent(origin_id)
    if isinstance(result, str):
        logging.warning(result)
        await msg.reply(result)
        return
    await msg.reply(render_recent_card(result))

@bot.command(name='bind')
async def bind_player(msg: Message, origin_id: str):
    result = request_API('bf1', 'player', {'name': origin_id})
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            logging.info(f'BF1 User {origin_id} not found')
        await msg.reply(f'玩家{origin_id}不存在')
        return
    user = msg.author
    exist_bind = db_op(conn, "SELECT id, originid FROM players WHERE id=?;", [user.id])
    if len(exist_bind):
        db_op(conn, "UPDATE players SET username=?, identify_num=?, personaid=?, originid=? WHERE id=?;",
                [user.username.lower(), user.identify_num, result['id'], result['userName'], user.id])
        await msg.reply(f'已解绑{exist_bind[0][1]}, 更新绑定{result["userName"]}')
    else:
        db_op(conn, 
              "INSERT INTO players VALUES(?, ?, ?, ?, ?);",
              [user.id, user.username.lower(), user.identify_num, result['id'], result['userName']])
        await msg.reply(f'已绑定{result["userName"]}')


@bot.command(name='account')
async def add_bf1admin_account(msg: Message, originid: str, remid: str, sid: str):
    if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
        return
    result = request_API('bf1', 'player', {'name': originid})
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            logging.info(f'BF1 User {originid} not found')
        await msg.reply(f'玩家{originid}不存在')
        return
    personaid = result['id']
    try:
        remid, sid, sessionid = upd_sessionID(remid, sid)
    except Exception as e:
        print(e)
        await msg.reply('无效remid/sid')
        return
    existing_account = db_op(conn, 'SELECT * FROM accounts WHERE personaid=?;', [personaid])
    if len(existing_account):
        db_op(conn, f"UPDATE accounts SET \
              remid=?, sid=?, sessionid=?, lastupdate=datetime('now'), originid=? WHERE personaid=?;",
            [remid, sid, sessionid, originid, personaid])
    else:
        db_op(conn, "INSERT INTO accounts  (personaid, remid, sid, originid, sessionid, lastupdate) \
            VALUES(?, ?, ?, ?, ?, datetime('now'));",
            [personaid, remid, sid, originid, sessionid])
    await msg.reply(f'{personaid}绑定/更新成功')

@bot.command(name='refresh')
async def refresh_sessionID(msg: Message, personaid: str):
    if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
        return
    existing_account = db_op(conn, 'SELECT personaid, remid, sid, originid FROM accounts WHERE personaid=?;', [personaid])
    if not len(existing_account):
        await msg.reply(f'账号{personaid}不存在')
        return
    try:
        remid, sid, sessionid = upd_sessionID(existing_account[0][1], existing_account[0][2])
        db_op(conn, "UPDATE accounts SET remid=?, sid=?, sessionid=?,\
              lastupdate=datetime('now') WHERE personaid=?;",
              [remid, sid, sessionid, personaid])
        await msg.reply(f'更新{personaid}({existing_account[0][3]})的sessionid成功')
    except Exception as e:
        await msg.reply('无效remid/sid')
        print(e)
        return


@bot.command(name='group')
async def server_group(msg: Message, group_name: str, owner: str, qq: str = None):
    if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
        return
    owner2 = split_kook_name(owner)
    if not owner2:
        await msg.reply('kook用户名不符合格式，请使用"用户名#数字表示符"格式')
        return
    user = db_op(conn, "SELECT * FROM players WHERE username=? AND identify_num=?;",
                 [owner2[0], owner2[1]])
    if not len(user):
        await msg.reply('群组所有者未绑定账号')
        return
    existing_group = db_op(conn, "SELECT * FROM server_groups WHERE name=?;", [group_name])
    if len(existing_group):
        await msg.reply(f'{group_name}已存在')
        return
    db_op(conn, "INSERT INTO server_groups (name, owner) VALUES(?, ?);", [group_name, user[0][0]])
    await msg.reply(f'已添加{group_name}')

@bot.command(name='chown')
async def change_group_owner(msg: Message, group_name: str, owner: str):
    if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
        return
    owner2 = split_kook_name(owner)
    if not owner2:
        await msg.reply('kook用户名不符合格式，请使用"用户名#数字表示符"格式')
        return
    user = db_op(conn, "SELECT id FROM players WHERE username=? AND identify_num=?;",
                 [owner2[0], owner2[1]])
    if not len(user):
        await msg.reply('群组所有者未绑定账号')
        return
    existing_group = db_op(conn, "SELECT serverid FROM server_groups WHERE name=?;", [group_name])
    if not len(existing_group):
        await msg.reply(f'{group_name}不存在')
        return
    db_op(conn, "UPDATE server_groups SET owner=? WHERE name=?;", [user[0][0], group_name])
    await msg.reply(f'群组{group_name}所有者更新为{owner}({user[0][0]})')

@bot.command(name='rmgroup')
async def remove_server_group(msg: Message, group_name: str):
    if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
        return
    existing_group = db_op(conn, "SELECT name FROM server_groups WHERE name=?;", [group_name])
    if not len(existing_group):
        await msg.reply(f'{group_name}不存在')
        return  
    db_op(conn, "DELETE FROM server_groups WHERE name=?", [group_name])
    await msg.reply(f'群组{group_name}已删除')


@bot.command(name='server')
async def add_server(msg: Message, gameid: str, group_name: str, group_num: int, bf1admin: str):
    if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
        return
    existing_group = db_op(conn, "SELECT name FROM server_groups WHERE name=?;", [group_name])
    if not len(existing_group):
        await msg.reply(f'群组{group_name}不存在')
        return
    existing_server_group = db_op(conn, "SELECT gameid FROM servers WHERE `group`=? AND group_num=?;",
                                  [group_name, group_num])
    if len(existing_server_group):
        await msg.reply(f'服务器编号{group_name}{group_num}已绑定为{existing_server_group[0][0]}')
        return
    existing_server = request_API('bf1', 'detailedserver', {'gameid': gameid})
    if isinstance(existing_server, requests.Response):
        if existing_server.status_code == 404:
            logging.info(f'server {gameid} not found')
        await msg.reply(f'服务器{gameid}不存在')
        return
    existing_admin = db_op(conn, "SELECT personaid FROM accounts WHERE originid=?;", [bf1admin.lower()])
    if not len(existing_admin):
        await msg.reply(f'管理员{bf1admin}不存在')
        return
    db_op(conn, "INSERT INTO servers VALUES (?, ?, ?, ?, ?);", 
          [gameid, existing_server['serverId'], group_name, group_num, existing_admin[0][0]])
    await msg.reply(f"已添加服务器{group_name}#{group_num}:{gameid},管理员账号{bf1admin}")

@bot.command(name='rmserver')
async def remove_server(msg: Message, group_name: str, group_num: int):
    if msg.author.username.lower()  + '#' + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
        return
    existing_server_group = db_op(conn, "SELECT gameid FROM servers WHERE `group`=? AND group_num=?;",
                                  [group_name, group_num])
    if not len(existing_server_group):
        await msg.reply(f'服务器编号{group_name}{group_num}不存在')
        return
    db_op(conn, "DELETE FROM servers WHERE `group`=? AND group_num=?;", [group_name, group_num])
    await msg.reply(f"已删除服务器{group_name}#{group_num}")


@bot.command(name='admin')  
async def add_admin(msg:Message, group_name: str, kook: str):
    existing_group = db_op(conn, "SELECT name FROM server_groups WHERE name=?;", [group_name])
    if not len(existing_group):
        await msg.reply(f'群组{group_name}不存在')
        return
    if not check_owner_perm(conn, msg.author, group_name, super_admin):
        await msg.reply('你没有权限，只有超管/群组所有者可以添加管理员')
        return
    kook_name = split_kook_name(kook)
    if not kook_name:
        await msg.reply('kook用户名不符合格式，请使用"用户名#数字表示符"格式')
        return
    existing_player = db_op(conn, "SELECT id, originid FROM players WHERE username=? AND identify_num=?;", kook_name)
    if not len(existing_player):
        await msg.reply('所添加管理员没有绑定Kook账号')
        return
    existing_admin = db_op(conn, "SELECT id FROM server_admins WHERE id=? AND `group`=?;",
                           [existing_player[0][0], group_name])
    if len(existing_admin):
        await msg.reply('该账号已是管理员')
        return
    db_op(conn, "INSERT INTO server_admins VALUES (?, ?, ?)",
          [existing_player[0][0], existing_player[0][1], group_name])
    await msg.reply(f'已添加管理员{kook}({existing_player[0][1]})至群组{group_name}')

@bot.command(name='rmadmin')
async def drop_admin(msg:Message, group_name: str, kook: str):
    # check server group
    existing_group = db_op(conn, "SELECT name FROM server_groups WHERE name=?;", [group_name])
    if not len(existing_group):
        await msg.reply(f'群组{group_name}不存在')
        return
    # check perm
    if not check_owner_perm(conn, msg.author, group_name, super_admin):
        await msg.reply('你没有权限，只有超管/群组所有者可以移除管理员')
        return
    # check kook username
    kook_name = split_kook_name(kook)
    if not kook_name:
        await msg.reply('kook用户名不符合格式，请使用"用户名#数字表示符"格式')
        return
    # check if given originid is binded to a kook user
    existing_player = db_op(conn, "SELECT id, originid FROM players WHERE username=? AND identify_num=?;", kook_name)
    if not len(existing_player):
        await msg.reply('该管理员不存在，用户没有绑定Kook账号')
        return
    # check if the given user is really an admin
    existing_admin = db_op(conn, "SELECT id FROM server_admins WHERE id=? AND `group`=?;",
                           [existing_player[0][0], group_name])
    if not len(existing_admin):
        await msg.reply('不存在该管理员或群组')
        return
    # remove admin
    db_op(conn, "DELETE FROM server_admins WHERE id=? AND `group`=?;",
          [existing_player[0][0], group_name])
    await msg.reply(f'已从群组{group_name}中移除管理员{kook}({existing_player[0][1]})')


@bot.command(name='map')
async def bf1_map(msg:Message, group_name: str, group_num: int, map_name: str):
    # Check if the server nickname exists in the database and retrieve gameid, serverid
    server = check_server_by_db(conn, group_name, group_num)
    if not server:
        await msg.reply(f'服务器{group_name}#{group_num}不存在')
        return
    # check permission
    if not check_admin_perm(conn, msg.author, group_name, super_admin):
        await msg.reply(f'你没有超管/群组管理员权限')
        return
    # find if the given map name is valid
    if map_name not in map_zh_dict:
        await msg.reply(f'地图{map_name}不存在')
        return
    # get admin account
    admin = db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                  (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                  [group_name, group_num])
    # Perform operation
    try:
        # Get server details to find the index of dersired maps
        server_res = rsp_API(method_name='GameServer.getFullServerDetails', 
                             params={'gameId': str(server[0])}, sessionID=admin[0][1])
        server_map_list = [map_item['mapPrettyName'] for map_item in server_res['result']['serverInfo']['rotation']]
        # change map
        res = rsp_API(method_name='RSP.chooseLevel', params={
            "persistedGameId": str(server[1]),
            "levelIndex": server_map_list.index(map_zh_dict[map_name])
        }, sessionID=admin[0][1])
        await msg.reply(f"已切换地图为{map_zh_dict[map_zh_dict[map_name]]}")
    except ValueError:
        await msg.reply('当前服务器图池中不存在该地图') # If the given map is not in server map pool
    except SessionIdError as se:
        if se.msg == 'ServerNotRestartableException':
            await msg.reply(f"服务器未开启") # If the server is not started
        else: # other sparta errors, might because the session id expired
            await msg.reply(f"{se.msg}\n可能是{admin[0][2]}({admin[0][0]})的sessionID过期，请联系超管刷新")
    except requests.HTTPError as e: # network error
        await msg.reply(f'网络错误：{str(e)}')

@bot.command(name='kick')
async def bf1_kick(msg:Message, group_name: str, group_num: int, originid: str, reason: str = None):
    # Check if the server nickname exists in the database and retrieve gameid, serverid
    server = check_server_by_db(conn, group_name, group_num)
    if not server:
        await msg.reply(f'服务器{group_name}#{group_num}不存在')
        return
    # check permission
    if not check_admin_perm(conn, msg.author, group_name, super_admin):
        await msg.reply(f'你没有超管/群组管理员权限')
        return
    # Search for targeted player that will get kicked
    result = request_API('bf1', 'player', {'name': originid})
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            logging.info(f'BF1 User {originid} not found')
        await msg.reply(f'玩家{originid}不存在')
        return
    # Find the admin account
    admin = db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                  (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                  [group_name, group_num])
    # Perform operation
    try:
        rsp_API('RSP.kickPlayer', {
            "game": "tunguska",
            "gameId": str(server[0]),
            "personaId": str(result['id']),
            "reason": zhconvert(reason) if reason else 'GENERAL'
        }, sessionID=admin[0][1])
        await msg.reply(f"从{group_name}#{group_num}中踢出{result['userName']}({reason})")
    except SessionIdError as se:
        if se.status_code == 403:
            await msg.reply(f"{admin[0][2]}({admin[0][0]})的sessionID过期，请联系超管刷新")
        elif se.status_code == 422:
            await msg.reply(f"无法踢出管理员或服务器绑定账号{admin[0][2]}({admin[0][0]})无权限")
        else:
            await msg.reply(f"{se.msg}\n可能是{admin[0][2]}({admin[0][0]})的sessionID过期，请联系超管刷新")
    except Exception as e:
        await msg.reply(str(e))
        

@bot.command(name='move')
async def bf1_move(msg:Message, group_name: str, group_num: int, originid: str):
    # Check if the server nickname exists in the database
    server = check_server_by_db(conn, group_name, group_num)
    if not server:
        await msg.reply(f'服务器{group_name}#{group_num}不存在')
        return
    # check permission
    if not check_admin_perm(conn, msg.author, group_name, super_admin):
        await msg.reply(f'你没有超管/群组管理员权限')
        return
    # Search for targeted player that will be switched team
    res_p = request_API('bf1', 'player', {'name': originid})
    if isinstance(res_p, requests.Response):
        if res_p.status_code == 404:
            logging.info(f'BF1 User {originid} not found')
        await msg.reply(f'玩家{originid}不存在')
        return
    # Find player list of the given server
    res_pl = request_API('bf1', 'players', {'gameid': server[0]})
    if isinstance(res_pl, requests.Response):
        await msg.reply('网络错误，请重试，可能是服务器未开启')
        return
    # Find the targeted player in playerlist
    team1, team2 = res_pl['teams']
    team1_pid = [p['player_id'] if 'player_id' in p else -1 for p in team1['players']]
    team2_pid = [p['player_id'] if 'player_id' in p else -1 for p in team2['players']]
    if res_p['id'] in team1_pid:
        teamid = team1['teamid']
        new_team_name = team2['key']
    elif res_p['id'] in team2_pid:
        teamid = team2['teamid']
        new_team_name = team1['key']
    else:
        await msg.reply(f"玩家{res_p['userName']}不在服务器中")
        return
    teamid = 1 if teamid == 'teamOne' else 2
    # Find the admin account
    admin = db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                  (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                  [group_name, group_num])
    # Perform operation
    try:
        rsp_API('RSP.movePlayer', {
            "game": "tunguska",
            "gameId": str(server[0]),
            "personaId": str(res_p['id']),
            "teamId": str(teamid),
            "forceKill": "true",
            "moveParty": "false"
        }, sessionID=admin[0][1])
        if new_team_name in zh_team_name_by_key:
            new_team_name = zh_team_name_by_key[new_team_name]
        await msg.reply(f"已将{group_name}#{group_num}中的{res_p['userName']}移动至队伍{3-teamid}({new_team_name})")
    except SessionIdError as se:
        if se.status_code == 403:
            await msg.reply(f"{admin[0][2]}({admin[0][0]})的sessionID过期，请联系超管刷新")
        elif se.status_code == 422:
            await msg.reply(f"玩家不在服务器中，或{admin[0][2]}({admin[0][0]})无权限")
        else:
            await msg.reply(f"{se.msg}\n可能是{admin[0][2]}({admin[0][0]})的sessionID过期，请联系超管刷新")
    except Exception as e:
        await msg.reply(str(e))


@bot.command(name='ban')
async def bf1_ban(msg:Message, group_name: str, originid: str, reason: str = None):
    pass

@bot.command(name='unban')
async def bf1_unban(msg:Message, group_name: str, originid: str):
    pass

@bot.command(name="pl")
async def bf1_playerlist(msg: Message, group_name: str, originid: str):
    pass

# 机器人限时vip数据不互通，暂时不开发
# @bot.command(name='vip')
# async def bf1_vip(msg:Message, group_name: str, group_num: int, originid: str, date: int = None):
#     pass

# @bot.command(name='unvip')
# async def bf1_unvip(msg:Message, group_name: str, group_num: int, originid: str):
#     pass

# @bot.command(name='viplist')
# async def bf1_viplist(msg:Message, group_name: str, group_num: int):
#     pass

# @bot.command(name='checkvip')
# async def bf1_checkvip(msg:Message, group_name: str, group_num: int):
#     pass


logging.basicConfig(level='INFO')
atexit.register(close_db)
bot.run()