import time
from khl.card import CardMessage, Card, Module, Element, Types, Struct

def render_stat_card(d: dict, top_n: int = 3) -> CardMessage:
    """
    Render card message for /stat
    """
    platoon = f"[{d['activePlatoon']['tag']}]" if d['activePlatoon']['tag'] else ''
    c1 = Card(
        Module.Header(f"战地1统计数据 - {platoon}{d['userName']}"),
        Module.Divider(),
        Module.Section(Element.Text("**基本数据**\n")),
        Module.Section(Struct.Paragraph(
            3,
            Element.Text(f"**等级**:\n{d['rank']}"),
            Element.Text(f"**游戏时间**:\n{round(d['secondsPlayed']/3600, 2)}小时"),
            Element.Text(f"**击杀**:\n{d['kills']}"),
            Element.Text(f"**死亡**:\n{d['deaths']}"),
            Element.Text(f"**KD**:\n{d['killDeath']}"),
            Element.Text(f"**KPM**:\n{d['killsPerMinute']}"),
            Element.Text(f"**SPM**:\n{d['scorePerMinute']}"),
            Element.Text(f"**复活**:\n{d['revives']}"),
            Element.Text(f"**治疗**:\n{d['heals']}"),
            Element.Text(f"**修理**:\n{d['repairs']}"),
            Element.Text(f"**命中**:\n{d['accuracy']}"),
            Element.Text(f"**爆头**:\n{d['headshots']}"),
            Element.Text(f"**最远爆头**:\n{d['longestHeadShot']}"),
            Element.Text(f"**胜率**:\n{d['winPercent']}"),
            Element.Text(f"**最高连杀**:\n{d['highestKillStreak']}")
        )),
        Module.Section(
            f"最后更新于{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"
        ),
        theme=Types.Theme.SUCCESS, size=Types.Size.LG
    )
    
    weapons = sorted(d['weapons'], key=lambda k: k['kills'], reverse=True)[0:top_n]
    c2 = Card(
        Module.Section(Element.Text("**武器信息**\n")), 
        theme=Types.Theme.SUCCESS, size=Types.Size.LG
    )
    for w in weapons:
        c2.append(Module.Section(Struct.Paragraph(
            3,
            Element.Text(f"**{w['weaponName']}**"),
            Element.Text(f"**游戏时间**:\n{round(w['timeEquipped']/3600, 2)}小时"),
            Element.Text(f"**击杀**:\n{w['kills']}"),
            Element.Text(f"**命中**:\n{w['accuracy']}"),
            Element.Text(f"**KPM**:\n{w['killsPerMinute']}"),
            Element.Text(f"**爆头**:\n{w['headshotKills']}"),
            Element.Text(f"**爆头率**:\n{w['headshots']}"),
            Element.Text(f"**效率**:\n{w['hitVKills']}")
        )))

    vehicles = sorted(d['vehicles'], key=lambda k: k['kills'], reverse=True)[0:top_n]
    c3 = Card(
        Module.Section(Element.Text("**载具信息**\n")), 
        theme=Types.Theme.SUCCESS, size=Types.Size.LG
    )
    for v in vehicles:
        c3.append(Module.Section(Struct.Paragraph(
            3, 
            Element.Text(f"**{v['vehicleName']}**"),
            Element.Text(f"**游戏时间**:\n{round(v['timeIn']/3600, 2)}小时"),
            Element.Text(f"**击杀**:\n{v['kills']}"),
            Element.Text(""),
            Element.Text(f"**KPM**:\n{v['killsPerMinute']}"),
            Element.Text(f"**摧毁**:\n{v['destroyed']}")
        )))

    return CardMessage(c1, c2, c3)

def render_find_server_card(d: dict):
    c = Card(theme=Types.Theme.SUCCESS, size=Types.Size.LG)
    n = len(d['servers'])
    for i in range(n):
        server = d['servers'][i]
        c.append(Module.Section(Element.Text(f"**{server['prefix']}**\n")))
        c.append(
            Module.Section(Struct.Paragraph(
                3,
                Element.Text(f"人数[排队]:\n{server['serverInfo']}[{server['inQue']}]"),
                Element.Text(f"模式:\n{server['mode']}"),
                Element.Text(f"地图:\n{server['currentMap']}"),
            ))
        )
        c.append(Module.Divider())
    c.append(Module.Section("最多显示10条结果"))
    return CardMessage(c)

def render_recent_card(d: list):
    c = Card(theme=Types.Theme.SUCCESS, size=Types.Size.LG)
    n = len(d)
    for i in range(n):
        c.append(Module.Section(Element.Text(f"{d[i]['server']}\n")))
        c.append(
            Module.Section(Struct.Paragraph(
                3,
                Element.Text(f"模式:\n{d[i]['mode']}"),
                Element.Text(f"地图:\n{d[i]['map']}"),
                Element.Text(f"结果:\n{d[i]['result']}"),
                Element.Text(f"击杀:\n{d[i]['Kills']}"),
                Element.Text(f"死亡:\n{d[i]['Deaths']}"),
                Element.Text(f"KD:\n{d[i]['kd']}"),
                Element.Text(f"时长:\n{d[i]['duration']}"),
                Element.Text(f"KPM:\n{d[i]['kpm']}"),
                Element.Text(f"得分:\n{d[i]['Score']}")
            ))
        )
        c.append(Module.Divider())
    return CardMessage(c)