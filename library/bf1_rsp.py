import requests
import logging

from khl import Bot, Message
from sqlite3 import Connection

from .util_dict import map_zh_dict, zh_team_name_by_key
from .utils import (
    request_API, db_op, zhconvert,
    check_admin_perm, check_server_by_db, rsp_API, SessionIdError
)

def init_rsp(bot: Bot, conn: Connection, super_admin: list):
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
    
    # @bot.command(name='ban')
    # async def bf1_ban(msg:Message, group_name: str, originid: str, reason: str = None):
    #     pass

    # @bot.command(name='unban')
    # async def bf1_unban(msg:Message, group_name: str, originid: str):
    #     pass

    # @bot.command(name="pl")
    # async def bf1_playerlist(msg: Message, group_name: str, originid: str):
    #     pass

    # # 机器人限时vip数据不互通
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