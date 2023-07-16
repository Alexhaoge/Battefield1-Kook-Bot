import logging

from khl import Bot, Message
# from aiosqlite import Connection
from httpx import Response

from .utils import (
    request_API, upd_sessionID, async_db_op
)


def init_account(bot: Bot, conn: str, super_admin: list):
    @bot.command(name='bind')
    async def bind_player(msg: Message, origin_id: str):
        result = request_API('bf1', 'player', {'name': origin_id})
        if isinstance(result, Response):
            if result.status_code == 404:
                logging.info(f'BF1 User {origin_id} not found')
            await msg.reply(f'玩家{origin_id}不存在')
            return
        user = msg.author
        exist_bind = await async_db_op(conn, "SELECT id, originid FROM players WHERE id=?;", [user.id])
        if len(exist_bind):
            await async_db_op(conn, "UPDATE players SET username=?, identify_num=?, personaid=?, originid=? WHERE id=?;",
                    [user.username.lower(), user.identify_num, result['id'], result['userName'], user.id])
            await msg.reply(f'已解绑{exist_bind[0][1]}, 更新绑定{result["userName"]}')
        else:
            await async_db_op(conn, 
                "INSERT INTO players VALUES(?, ?, ?, ?, ?);",
                [user.id, user.username.lower(), user.identify_num, result['id'], result['userName']])
            await msg.reply(f'已绑定{result["userName"]}')


    @bot.command(name='account')
    async def add_bf1admin_account(msg: Message, originid: str, remid: str, sid: str):
        if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
            await msg.reply('你不是超级管理员')
            return
        result = request_API('bf1', 'player', {'name': originid})
        if isinstance(result, Response):
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
        existing_account = await async_db_op(conn, 'SELECT * FROM accounts WHERE personaid=?;', [personaid])
        if len(existing_account):
            await async_db_op(conn, f"UPDATE accounts SET \
                remid=?, sid=?, sessionid=?, lastupdate=datetime('now'), originid=? WHERE personaid=?;",
                [remid, sid, sessionid, originid, personaid])
        else:
            await async_db_op(conn, "INSERT INTO accounts  (personaid, remid, sid, originid, sessionid, lastupdate) \
                VALUES(?, ?, ?, ?, ?, datetime('now'));",
                [personaid, remid, sid, originid, sessionid])
        await msg.reply(f'{personaid}绑定/更新成功')

    @bot.command(name='refresh')
    async def refresh_sessionID(msg: Message, personaid: str):
        if msg.author.username.lower() + '#' + msg.author.identify_num not in super_admin:
            await msg.reply('你不是超级管理员')
            return
        existing_account = await async_db_op(conn, 'SELECT personaid, remid, sid, originid FROM accounts WHERE personaid=?;', [personaid])
        if not len(existing_account):
            await msg.reply(f'账号{personaid}不存在')
            return
        try:
            remid, sid, sessionid = upd_sessionID(existing_account[0][1], existing_account[0][2])
            await async_db_op(conn, "UPDATE accounts SET remid=?, sid=?, sessionid=?,\
                lastupdate=datetime('now') WHERE personaid=?;",
                [remid, sid, sessionid, personaid])
            await msg.reply(f'更新{personaid}({existing_account[0][3]})的sessionid成功')
        except Exception as e:
            await msg.reply('无效remid/sid')
            print(e)
            return