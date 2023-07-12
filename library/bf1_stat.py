from khl import Bot, Message
from sqlite3 import Connection
from requests import Response
import logging


from .cardTemplate import (
    render_stat_card, render_find_server_card, render_recent_card
)
from .utils import (
    request_API, async_bftracker_recent, db_op
)

def init_stat(bot: Bot, conn: Connection):
    
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
        if isinstance(result, Response):
            if result.status_code == 404:
                logging.info(f'BF1 User {origin_id} not found')
            await msg.reply(f'玩家{origin_id}不存在')
            return
        await msg.reply(render_stat_card(result))

    @bot.command(name='f')
    async def bf1_find_server(msg: Message, server_name: str):
        result = request_API('bf1', 'servers', {'name': server_name, 'lang':'zh-tw'})
        if isinstance(result, Response):
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