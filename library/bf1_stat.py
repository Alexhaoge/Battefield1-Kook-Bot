import logging
import httpx
import bs4
import re

from khl import Bot, Message
# from aiosqlite import Connection
from httpx import Response
from typing import Union
from asyncio import create_task, gather

from .cardTemplate import (
    render_stat_card, render_find_server_card, render_recent_card
)
from .utils import (
    request_API, async_request_API, fetch_data, async_db_op
)


def init_stat(bot: Bot, conn: str):
    
    @bot.command(name='stat', aliases=['s'])
    async def bf1_player_stat(msg: Message, origin_id: str = None):
        """
        /stat originid
        """
        if origin_id is None:
            user = await async_db_op(conn, "SELECT originid FROM players WHERE id=?;", [msg.author.id])
            if len(user):
                origin_id = user[0][0]
            else:
                await msg.reply(f'未绑定账号')
                return
        result = await async_request_API('bf1','all',{'name':origin_id, 'lang':'zh-tw'})
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

    @bot.command(name='recent', aliases= ['r'])
    async def bf1_recent(msg: Message, origin_id: str = None):
        if origin_id is None:
            user = await async_db_op(conn, "SELECT originid FROM players WHERE id=?;", [msg.author.id])
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