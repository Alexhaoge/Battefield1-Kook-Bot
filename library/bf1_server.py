import logging

from khl import Bot, Message
# from aiosqlite import Connection
from httpx import Response

from .utils import (
    request_API, async_db_op, check_owner_perm, split_kook_name
)

def init_server(bot: Bot, conn: str, super_admin: list):
    @bot.command(name='group')
    async def server_group(msg: Message, group_name: str, owner: str, qq: str = None):
        if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
            await msg.reply('你不是超级管理员')
            return
        owner2 = split_kook_name(owner)
        if not owner2:
            await msg.reply('kook用户名不符合格式，请使用"用户名#数字表示符"格式')
            return
        user = await async_db_op(conn, "SELECT * FROM players WHERE username=? AND identify_num=?;",
                    [owner2[0], owner2[1]])
        if not len(user):
            await msg.reply('群组所有者未绑定账号')
            return
        existing_group = await async_db_op(conn, "SELECT * FROM server_groups WHERE name=?;", [group_name])
        if len(existing_group):
            await msg.reply(f'{group_name}已存在')
            return
        await async_db_op(conn, "INSERT INTO server_groups (name, owner) VALUES(?, ?);", [group_name, user[0][0]])
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
        user = async_db_op(conn, "SELECT id FROM players WHERE username=? AND identify_num=?;",
                    [owner2[0], owner2[1]])
        if not len(user):
            await msg.reply('群组所有者未绑定账号')
            return
        existing_group = async_db_op(conn, "SELECT serverid FROM server_groups WHERE name=?;", [group_name])
        if not len(existing_group):
            await msg.reply(f'{group_name}不存在')
            return
        await async_db_op(conn, "UPDATE server_groups SET owner=? WHERE name=?;", [user[0][0], group_name])
        await msg.reply(f'群组{group_name}所有者更新为{owner}({user[0][0]})')

    @bot.command(name='rmgroup')
    async def remove_server_group(msg: Message, group_name: str):
        if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
            await msg.reply('你不是超级管理员')
            return
        existing_group = await async_db_op(conn, "SELECT name FROM server_groups WHERE name=?;", [group_name])
        if not len(existing_group):
            await msg.reply(f'{group_name}不存在')
            return  
        await async_db_op(conn, "DELETE FROM server_groups WHERE name=?", [group_name])
        await msg.reply(f'群组{group_name}已删除')


    @bot.command(name='server')
    async def add_server(msg: Message, gameid: str, group_name: str, group_num: int, bf1admin: str):
        if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
            await msg.reply('你不是超级管理员')
            return
        existing_group = await async_db_op(conn, "SELECT name FROM server_groups WHERE name=?;", [group_name])
        if not len(existing_group):
            await msg.reply(f'群组{group_name}不存在')
            return
        existing_server_group = await async_db_op(conn, "SELECT gameid FROM servers WHERE `group`=? AND group_num=?;",
                                    [group_name, group_num])
        if len(existing_server_group):
            await msg.reply(f'服务器编号{group_name}{group_num}已绑定为{existing_server_group[0][0]}')
            return
        existing_server = request_API('bf1', 'detailedserver', {'gameid': gameid})
        if isinstance(existing_server, Response):
            if existing_server.status_code == 404:
                logging.info(f'server {gameid} not found')
            await msg.reply(f'服务器{gameid}不存在')
            return
        existing_admin = await async_db_op(conn, "SELECT personaid FROM accounts WHERE originid=?;", [bf1admin.lower()])
        if not len(existing_admin):
            await msg.reply(f'管理员{bf1admin}不存在')
            return
        await async_db_op(conn, "INSERT INTO servers VALUES (?, ?, ?, ?, ?);", 
            [gameid, existing_server['serverId'], group_name, group_num, existing_admin[0][0]])
        await msg.reply(f"已添加服务器{group_name}#{group_num}:{gameid},管理员账号{bf1admin}")

    @bot.command(name='rmserver')
    async def remove_server(msg: Message, group_name: str, group_num: int):
        if msg.author.username.lower()  + '#' + msg.author.identify_num not in super_admin:
            await msg.reply('你不是超级管理员')
            return
        existing_server_group = await async_db_op(conn, "SELECT gameid FROM servers WHERE `group`=? AND group_num=?;",
                                    [group_name, group_num])
        if not len(existing_server_group):
            await msg.reply(f'服务器编号{group_name}{group_num}不存在')
            return
        await async_db_op(conn, "DELETE FROM servers WHERE `group`=? AND group_num=?;", [group_name, group_num])
        await msg.reply(f"已删除服务器{group_name}#{group_num}")


    @bot.command(name='admin')  
    async def add_admin(msg:Message, group_name: str, kook: str):
        existing_group = await async_db_op(conn, "SELECT name FROM server_groups WHERE name=?;", [group_name])
        if not len(existing_group):
            await msg.reply(f'群组{group_name}不存在')
            return
        permission = await check_owner_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply('你没有权限，只有超管/群组所有者可以添加管理员')
            return
        kook_name = split_kook_name(kook)
        if not kook_name:
            await msg.reply('kook用户名不符合格式，请使用"用户名#数字表示符"格式')
            return
        existing_player = await async_db_op(conn, "SELECT id, originid FROM players WHERE username=? AND identify_num=?;", kook_name)
        if not len(existing_player):
            await msg.reply('所添加管理员没有绑定Kook账号')
            return
        existing_admin = await async_db_op(conn, "SELECT id FROM server_admins WHERE id=? AND `group`=?;",
                            [existing_player[0][0], group_name])
        if len(existing_admin):
            await msg.reply('该账号已是管理员')
            return
        await async_db_op(conn, "INSERT INTO server_admins VALUES (?, ?, ?)",
            [existing_player[0][0], existing_player[0][1], group_name])
        await msg.reply(f'已添加管理员{kook}({existing_player[0][1]})至群组{group_name}')

    @bot.command(name='rmadmin')
    async def drop_admin(msg:Message, group_name: str, kook: str):
        # check server group
        existing_group = await async_db_op(conn, "SELECT name FROM server_groups WHERE name=?;", [group_name])
        if not len(existing_group):
            await msg.reply(f'群组{group_name}不存在')
            return
        # check permission
        permission = await check_owner_perm(conn, msg.author, group_name, super_admin)
        if not permission:
            await msg.reply('你没有权限，只有超管/群组所有者可以移除管理员')
            return
        # check kook username
        kook_name = split_kook_name(kook)
        if not kook_name:
            await msg.reply('kook用户名不符合格式，请使用"用户名#数字表示符"格式')
            return
        # check if given originid is binded to a kook user
        existing_player = await async_db_op(conn, "SELECT id, originid FROM players WHERE username=? AND identify_num=?;", kook_name)
        if not len(existing_player):
            await msg.reply('该管理员不存在，用户没有绑定Kook账号')
            return
        # check if the given user is really an admin
        existing_admin = await async_db_op(conn, "SELECT id FROM server_admins WHERE id=? AND `group`=?;",
                            [existing_player[0][0], group_name])
        if not len(existing_admin):
            await msg.reply('不存在该管理员或群组')
            return
        # remove admin
        await async_db_op(conn, "DELETE FROM server_admins WHERE id=? AND `group`=?;",
            [existing_player[0][0], group_name])
        await msg.reply(f'已从群组{group_name}中移除管理员{kook}({existing_player[0][1]})')