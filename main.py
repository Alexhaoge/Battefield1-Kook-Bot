import logging
import sqlite3
import requests
import atexit

from khl import Bot, Message, MessageTypes, User
from secret import token, super_admin
from random import choice

from library.utils import (
    request_API, async_bftracker_recent, db_op, verify_originid
)
from library.cardTemplate import (
    render_stat_card, render_find_server_card, render_recent_card
)

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
        user = db_op(conn, f"SELECT originid FROM players WHERE id={msg.author.id};")
        if len(user):
            origin_id = user[0]
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
        user = db_op(conn, f"SELECT originid FROM players WHERE id={msg.author.id};")
        if len(user):
            origin_id = user[0]
        else:
            await msg.reply(f'未绑定账号')
            return
    result = await async_bftracker_recent(origin_id)
    if isinstance(result, str):
        logging.warning(result)
        await msg.reply(result)
        return
    await msg.reply(render_recent_card(result))
    #await msg.reply(cm)

@bot.command(name='bind')
async def bind_player(msg: Message, origin_id: str):
    result = request_API('bf1', 'player', {'name': origin_id})
    if isinstance(result, requests.Response):
        if result.status_code == 404:
            logging.info(f'BF1 User {origin_id} not found')
        await msg.reply(f'玩家{origin_id}不存在')
        return
    user = msg.author
    exist_bind = db_op(conn, f"SELECT id FROM players WHERE id={user.id};")
    if len(exist_bind):
        db_op(conn, f"UPDATE players SET username='{user.username}',\
              identify_num={user.identify_num}, personaid={result['id']},\
                originid='{origin_id}' WHERE id={user.id};")
        await msg.reply('已更新绑定')
    else:
        sql = f"INSERT INTO players VALUES(\
              {user.id}, '{user.username}', {user.identify_num},\
                {result['id']}, '{result['userName']}');"
        #print(sql)
        db_op(conn, sql)
        await msg.reply('已绑定')

@bot.command(name='account')
async def add_bf1admin_account(msg: Message, originid: str, remid: str, sid: str):
    if msg.author.username + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
    pass

@bot.command(name='addgroup')
async def add_server_group(msg: Message, group_name: str, owner: str, qq: str = None):
    if msg.author.username + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
    pass

@bot.command(name='chown')
async def change_server_group_owner(msg: Message, group_name: str, owner: str):
    if msg.author.username + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
    pass

@bot.command(name='rmgroup')
async def remove_server_group(msg: Message, group_name: str):
    if msg.author.username + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
    pass

@bot.command(name='addserver')
async def add_server(msg: Message, gameid: str, group_name: str, group_num: int, bf1admin: int):
    if msg.author.username + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
    pass

@bot.command(name='rmserver')
async def remove_server(msg: Message, group_name: str, group_num: int):
    if msg.author.username + msg.author.identify_num not in super_admin:
        await msg.reply('你不是超级管理员')
    pass

@bot.command(name='addadmin')
async def add_admin(msg:Message, group_name: str, origin_id: str):
    pass

@bot.command(name='rmadmin')
async def drop_admin(msg:Message, group_name: str, origin_id: str):
    pass

@bot.command(name='map')
async def bf1_map(msg:Message, group_name: str, group_num: int, map_name: str):
    pass

@bot.command(name='kick')
async def bf1_kick(msg:Message, group_name: str, group_num: int, originid: str, reason: str = None):
    pass

@bot.command(name='move')
async def bf1_move(msg:Message, group_name: str, group_num: int, originid: str, side: str):
    pass

@bot.command(name='ban')
async def bf1_ban(msg:Message, group_name: str, originid: str, reason: str = None):
    pass

@bot.command(name='unban')
async def bf1_unban(msg:Message, group_name: str, originid: str):
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