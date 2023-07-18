import logging

from khl import Bot, Message, MessageTypes
# from aiosqlite import Connection
from asyncio import create_task, gather
from httpx import Response
from traceback import format_exc
from datetime import date, timedelta

from .util_dict import map_zh_dict, zh_team_name_by_key
from .utils import (
    request_API, async_request_API, async_rsp_API, 
    async_db_op, zhconvert,
    check_admin_perm, check_server_by_db, RSPException
)

def init_rsp(bot: Bot, conn: str, super_admin: list):
    
    ##############################################################################################
    # Change map
    ##############################################################################################
    @bot.command(name='map')
    async def bf1_map(msg:Message, group_name: str, group_num: int, map_name: str):
        # Check if the server nickname exists in the database and retrieve gameid, serverid
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有超管/群组管理员权限')
            return
        # find if the given map name is valid
        if map_name not in map_zh_dict:
            await msg.reply(f'地图{map_name}不存在')
            return
        # get admin account
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        # Perform operation
        try:
            # Get server details to find the index of dersired maps
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                params={'gameId': str(server[0])}, sessionID=admin[0][1])
            server_map_list = [map_item['mapPrettyName'] for map_item in server_res['result']['serverInfo']['rotation']]
            # change map
            res = await async_rsp_API(method_name='RSP.chooseLevel', params={
                "persistedGameId": str(server[1]),
                "levelIndex": server_map_list.index(map_zh_dict[map_name])
            }, sessionID=admin[0][1])
            await msg.reply(f"已切换地图为{map_zh_dict[map_zh_dict[map_name]]}")
        except ValueError:
            await msg.reply('当前服务器图池中不存在该地图') # If the given map is not in server map pool
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))


    # Kick player
    @bot.command(name='kick', aliases=['k'])
    async def bf1_kick(msg:Message, group_name: str, group_num: int, originid: str, reason: str = None):
        # Check if the server nickname exists in the database and retrieve gameid, serverid
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有超管/群组管理员权限')
            return
        # Search for targeted player that will get kicked
        result = request_API('bf1', 'player', {'name': originid})
        if isinstance(result, Response):
            await msg.reply(f'玩家{originid}不存在')
            return
        # Find the admin account
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        # Perform operation
        try:
            await async_rsp_API('RSP.kickPlayer', {
                "game": "tunguska",
                "gameId": str(server[0]),
                "personaId": str(result['id']),
                "reason": zhconvert(reason) if reason else 'GENERAL'
            }, sessionID=admin[0][1])
            await msg.reply(f"从{group_name}#{group_num}中踢出{result['userName']}({reason})")
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))


    ##############################################################################################
    # Switch player's side
    ##############################################################################################
    @bot.command(name='move')
    async def bf1_move(msg:Message, group_name: str, group_num: int, originid: str):
        # Check if the server nickname exists in the database
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        # Search for targeted player that will be switched team
        res_p = request_API('bf1', 'player', {'name': originid})
        if isinstance(res_p, Response):
            await msg.reply(f'玩家{originid}不存在')
            return
        # Find player list of the given server
        res_pl = request_API('bf1', 'players', {'gameid': server[0]})
        if isinstance(res_pl, Response):
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
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        # Perform operation
        try:
            await async_rsp_API('RSP.movePlayer', {
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
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))


    ##############################################################################################
    # Ban and unban
    ##############################################################################################
    @bot.command(name='ban')
    async def bf1_ban(msg:Message, group_name: str, group_num: int, originid: str, reason: str = None):
        # Check if the server nickname exists in the database
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        # check if player exists and correct the originid
        player = request_API('bf1', 'player', {'name': originid})
        if isinstance(player, Response):
            await msg.reply(f'玩家{originid}不存在')
            return
        # Find the admin account
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        try:
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                params={'gameId': str(server[0])}, sessionID=admin[0][1])
            await async_rsp_API("RSP.addServerBan", params={
                "game": "tunguska",
                "serverId": str(server_res['result']['rspInfo']['server']['serverId']),
                "personaId": str(player['id']),
            }, sessionID=admin[0][1])
            await msg.reply(f"已在{group_name}#{group_num}中封禁玩家{player['userName']}({reason})")
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))
    
    @bot.command(name='unban')
    async def bf1_unban(msg:Message, group_name: str, group_num: int, originid: str):
        # Check if the server nickname exists in the database
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        player = request_API('bf1', 'player', {'name': originid})
        if isinstance(player, Response):
            await msg.reply(f'玩家{originid}不存在')
            return
        # Find the admin account
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        try:
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                params={'gameId': str(server[0])}, sessionID=admin[0][1])
            banned_pl = [int(p['personaId']) for p in server_res['result']['rspInfo']['bannedList']]
            print(player['id'])
            if not player['id'] in banned_pl:
                await msg.reply(f"玩家{player['userName']}未被封禁")
            else:
                await async_rsp_API("RSP.removeServerBan", params={
                    "game": "tunguska",
                    "serverId": str(server_res['result']['rspInfo']['server']['serverId']),
                    "personaId": str(player['id']),
                }, sessionID=admin[0][1])
                await msg.reply(f"已在{group_name}#{group_num}中解封玩家{player['userName']}")
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))


    ##############################################################################################
    # Ban/unban player from all server in one server group
    ##############################################################################################
    async def async_ban_helper(group_name: str, group_num: int, gameid: str, player: dict) -> str:
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        try:
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                    params={'gameId': str(gameid)}, sessionID=admin[0][1])
            await async_rsp_API("RSP.addServerBan", params={
                "game": "tunguska",
                "serverId": str(server_res['result']['rspInfo']['server']['serverId']),
                "personaId": str(player['id']),
            }, sessionID=admin[0][1])
            msg = f"封禁玩家{player['userName']}成功"
        except RSPException as se:
            msg = se.echo(admin[0][2], admin[0][0])
        except Exception as e:
            msg = format_exc(limit=2)
        return msg
    
    @bot.command(name="bana")
    async def bf1_ban_all(msg: Message, group_name: str, originid: str, reason: str = None):
        # Find all servers in this group
        servers = await async_db_op(conn, "SELECT `group`, group_num, gameid FROM servers WHERE `group`=? \
                                    ORDER BY group_num ASC;", 
                                   [group_name])
        if not len(servers):
            await msg.reply(f'服务器群组{group_name}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        # Check if player exists
        player = await async_request_API('bf1', 'player', {'name': originid})
        if isinstance(player, Response):
            await msg.reply(f'玩家{originid}不存在')
            return
        # create async ban task for each group
        tasks = [create_task(async_ban_helper(s[0], s[1], s[2], player)) for s in servers]
        # Gather echos
        echos = await gather(*tasks, return_exceptions=True)
        # Reply msg and return
        await msg.reply('\n'.join([f"{s[0]}#{s[1]}:{e}" for s, e in zip(servers, echos)]))

    async def async_unban_helper(group_name: str, group_num: int, gameid: str, player: dict) -> str:
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        try:
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                    params={'gameId': str(gameid)}, sessionID=admin[0][1])
            banned_pl = [int(p['personaId']) for p in server_res['result']['rspInfo']['bannedList']]
            if not player['id'] in banned_pl:
                msg = f"玩家{player['userName']}未被封禁"
            else:
                await async_rsp_API("RSP.removeServerBan", params={
                    "game": "tunguska",
                    "serverId": str(server_res['result']['rspInfo']['server']['serverId']),
                    "personaId": str(player['id']),
                }, sessionID=admin[0][1])
                msg = f"玩家{player['userName']}解封成功"
        except RSPException as se:
            msg = se.echo(admin[0][2], admin[0][0])
        except Exception as e:
            msg = format_exc(limit=2)
        return msg
        return msg

    @bot.command(name="unbana")
    async def bf1_unban_all(msg: Message, group_name: str, originid: str, reason: str = None):
        # Check if the server nickname exists in the database
        servers = await async_db_op(conn, "SELECT `group`, group_num, gameid FROM servers WHERE `group`=? \
                                    ORDER BY group_num ASC;", 
                                   [group_name])
        if not servers:
            await msg.reply(f'服务器群组{group_name}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        player = await async_request_API('bf1', 'player', {'name': originid})
        if isinstance(player, Response):
            await msg.reply(f'玩家{originid}不存在')
            return
        tasks = [create_task(async_unban_helper(s[0], s[1], s[2], player)) for s in servers]
        echos = await gather(*tasks, return_exceptions=True)
        await msg.reply('\n'.join([f"{s[0]}#{s[1]}:{e}" for s, e in zip(servers, echos)]))


    ##############################################################################################
    # Add and removing server VIPs (Temporary VIPs rely on our own db, not sync with other bots)
    ##############################################################################################
    @bot.command(name='vip')
    async def bf1_vip(msg:Message, group_name: str, group_num: int, originid: str, days: int = None):
        # Validate days:
        if (days is not None) and ((days <= 0) or (days > 365)):
            await msg.reply("请输入有效的VIP时限，必须是1~365的整数")
            return
        # Check if the server nickname exists in the database
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        # Search for targeted player
        player = await async_request_API('bf1', 'player', {'name': originid})
        if isinstance(player, Response):
            await msg.reply(f'玩家{originid}不存在')
            return 
        # Check if targeted player already have vip
        existing_vip = await async_db_op(conn, "SELECT expire FROM server_vips WHERE personaid=? AND gameid=?;",
                                             [player['id'], server[0]])
        if len(existing_vip):
            if (existing_vip[0][0] is None) and days:
                await msg.reply(f"玩家{player['id']}已经是{group_name}#{group_num}的永久vip")
                return
            expire = date.fromisoformat(existing_vip[0][0]) + timedelta(days=days) if days else None
        else:
            expire = date.today() + timedelta(days=days) if days else None
        # Find the admin account
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        try:
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                params={'gameId': str(server[0])}, sessionID=admin[0][1])
            await async_rsp_API("RSP.addServerVip", params={
                "game": "tunguska",
                "serverId": str(server_res['result']['rspInfo']['server']['serverId']),
                "personaId": str(player['id']),
            }, sessionID=admin[0][1])
            if len(existing_vip):
                await async_db_op(conn, "UPDATE server_vips SET expire=? WHERE personaid=? AND gameid=?;",
                                  [expire, player['id'], server[0]])
            else:
                await async_db_op(conn, "INSERT INTO server_vips (personaid, originid, gameid, expire) VALUES (?, ?, ? ,?)",
                                  [player['id'], player['userName'], server[0], expire])
            await msg.reply(f"已在{group_name}#{group_num}中为玩家{player['userName']}添加VIP({expire})")
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))

    @bot.command(name='unvip')
    async def bf1_unvip(msg:Message, group_name: str, group_num: int, originid: str):
        # Check if the server nickname exists in the database
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        # Search for targeted player
        player = await async_request_API('bf1', 'player', {'name': originid})
        if isinstance(player, Response):
            await msg.reply(f'玩家{originid}不存在')
            return
        # Check if targeted player have vip
        existing_vip = await async_db_op(conn, "SELECT personaid, gameid FROM server_vips WHERE personaid=? AND gameid=?;",
                                             [player['id'], server[0]])
        # Find the admin account
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        try:
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                params={'gameId': str(server[0])}, sessionID=admin[0][1])
            await async_rsp_API("RSP.removeServerVip", params={
                "game": "tunguska",
                "serverId": str(server_res['result']['rspInfo']['server']['serverId']),
                "personaId": str(player['id']),
            }, sessionID=admin[0][1])
            if len(existing_vip):
                await async_db_op(conn, "DELETE FROM server_vips WHERE personaid=? AND gameid=?;",
                                  [player['id'], server[0]])
            await msg.reply(f"已从{group_name}#{group_num}删除玩家{player['userName']}的VIP")
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))

    @bot.command(name='viplist')
    async def bf1_viplist(msg:Message, group_name: str, group_num: int):
        # Check if the server nickname exists in the database
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        try:
            # Find the vip list in db
            db_vips = await async_db_op(conn, "SELECT personaid, originid, expire FROM server_vips WHERE gameid=?;", [server[0]])
            db_vip_dict = {p[0]:(p[1], p[2] if p[2] else '永久') for p in db_vips}
            db_vip_pids_set = set(db_vip_dict.keys())
            # Find the vip list from EA API
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                params={'gameId': str(server[0])}, sessionID=admin[0][1])
            server_vips_dict = {int(p['personaId']):p['displayName'] for p in server_res['result']['rspInfo']['vipList']}
            server_vips_set = set(server_vips_dict.keys())
            # Deal with differences between two vip list
            db_vips_to_delete = list(db_vip_pids_set - server_vips_set)
            if len(db_vips_to_delete):
                await async_db_op(conn, "DELETE FROM server_vips WHERE gameid=? AND personaid IN ({})".format(",".join("?" * len(db_vip_dict))),
                                [server[0]] + db_vips_to_delete)
            vips_intersect = sorted([f"{db_vip_dict[pid][0]}({db_vip_dict[pid][1]})" 
                              for pid in server_vips_set.intersection(db_vip_pids_set)])
            vips_intersect_str = '  \n'.join(vips_intersect)
            vips_not_in_db = sorted([server_vips_dict[pid] for pid in (server_vips_set - db_vip_pids_set)])
            vips_not_in_db_str = '  \n'.join(vips_not_in_db)
            await msg.reply(f"{group_name}#{group_num}共有 **{len(server_vips_dict)}**个VIP  \n" +
                            f"机器人数据库记录VIP **{len(vips_intersect)}**个  \n{vips_intersect_str}  \n" +
                            f"非数据库记录VIP **{len(vips_not_in_db)}**个  \n{vips_not_in_db_str}  \n" +
                            f"机器人数据库删除不存在的VIP记录 **{len(db_vips_to_delete)}**个",
                            type=MessageTypes.KMD)
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))

    @bot.command(name='checkvip')
    async def bf1_checkvip(msg:Message, group_name: str, group_num: int):
        # Check if the server nickname exists in the database
        server = await check_server_by_db(conn, group_name, group_num)
        if not server:
            await msg.reply(f'服务器{group_name}#{group_num}不存在')
            return
        # check permission
        permission = await check_admin_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply(f'你没有{group_name}群组管理员权限')
            return
        admin = await async_db_op(conn, "SELECT personaid, sessionid, originid FROM accounts WHERE personaid IN \
                    (SELECT bf1admin FROM servers WHERE `group`=? AND group_num=?);",
                    [group_name, group_num])
        try:
            # Find the expired vip list in db
            db_expired_vips = await async_db_op(conn, "SELECT personaid, originid FROM server_vips \
                                        WHERE gameid=? AND expire < date('now');", [server[0]])
            # Find serverId
            server_res = await async_rsp_API(method_name='GameServer.getFullServerDetails', 
                                params={'gameId': str(server[0])}, sessionID=admin[0][1])
            serverid = server_res['result']['rspInfo']['server']['serverId']
            # Create tasks for each expired VIP and execute them
            tasks = [create_task(
                async_rsp_API("RSP.removeServerVip", params={
                    "game": "tunguska",
                    "serverId": str(serverid),
                    "personaId": str(v[0]),
                }, sessionID=admin[0][1]))
                for v in db_expired_vips
            ]
            # Filter echos, count errors(failed)
            echos = await gather(*tasks, return_exceptions=True)
            failed_ind = [i for i in range(len(echos)) if isinstance(echos[i], Exception)]
            success_ind = [i for i in range(len(echos)) if not isinstance(echos[i], Exception)]
            await async_db_op(conn, "DELETE FROM server_vips WHERE gameid=? AND personaid IN ({})".format(",".join("?" * len(success_ind))),
                              [server[0]] + [db_expired_vips[i][0] for i in success_ind])
            await msg.reply(f"成功删除**{len(success_ind)}**个过期VIP"+
                            (f"，**{len(failed_ind)}个VIP删除失败**:" if len(failed_ind) else '') + 
                            "\n  " + '\n  '.join([db_expired_vips[i][1] for i in failed_ind]),
                            type=MessageTypes.KMD)
        except RSPException as se:
            await msg.reply(se.echo(admin[0][2], admin[0][0]))
        except Exception as e:
            await msg.reply(format_exc(limit=2))


    # @bot.command(name="pl")
    # async def bf1_playerlist(msg: Message, group_name: str, originid: str):
    #     pass