import time
from khl.card import CardMessage, Card, Module, Element, Types, Struct, Theme

def render_card(d: dict, top_n: int = 3) -> CardMessage:
    c = Card(
        Module.Header(f"战地1统计数据 - [{d['activePlatoon']['tag']}]{d['userName']}"),
        Module.Divider(),
        Module.Section(Element.Text("**基本数据**\n")),
        Module.Section(Struct.Paragraph(
            cols=3, fields=[
                Element.Text(f"**等级**: {d['rank']}"),
                Element.Text(f"**游戏时间**: {d['secondsPlayed']/3600}"),
                Element.Text(f"**击杀**: {d['kills']}"),
                Element.Text(f"**死亡**: {d['deaths']}"),
                Element.Text(f"**KD**: {d['killDeath']}"),
                Element.Text(f"**KPM**: {d['killsPerMinute']}"),
                Element.Text(f"**SPM**: {d['scorePerMinute']}"),
                Element.Text(f"**复活**: {d['revives']}"),
                Element.Text(f"**治疗**: {d['heals']}"),
                Element.Text(f"**修理**: {d['repairs']}"),
                Element.Text(f"**命中**: {d['accuracy']}"),
                Element.Text(f"**爆头**: {d['headshots']}"),
                Element.Text(f"**最远爆头**: {d['rank']}"),
                Element.Text(f"**胜率**: {d['winPercent']}"),
                Element.Text(f"**最高连杀**: {d['highestKillStreak']}"),
            ]
        )),
        Module.Section(Element.Text("**武器信息**\n")),  
        theme=Types.Theme.SUCCESS, size=Types.Size.LG
    )
    
    weapons = sorted(d['weapons'], key=lambda k: k['kills'], reverse=True)[0:top_n]
    for w in weapons:
        c.append(Module.Section(Struct.Paragraph(
            cols=3, fields=[
                Element.Text(f"**{w['weaponName']}**"),
                Element.Text(f"**游戏时间**: {w['timeEquipped']/3600}"),
                Element.Text(f"**击杀**: {w['kills']}"),
                Element.Text(f"**命中**: {w['accuracy']}"),
                Element.Text(f"**KPM**: {w['killsPerMinute']}"),
                Element.Text(f"**爆头**: {w['headshotKills']}"),
                Element.Text(f"**爆头率**: {w['headshots']}"),
                Element.Text(f"**效率**: {w['hitVKills']}"),
            ]
        )))

    c.append(Module.Section(Element.Text("**载具信息**\n")))
    vehicles = sorted(d['vehicles'], key=lambda k: k['kills'], reverse=True)[0:top_n]
    for v in vehicles:
        c.append(Module.Section(Struct.Paragraph(
            cols=3, fields=[
                Element.Text(f"**{v['vehicleName']}**"),
                Element.Text(f"**游戏时间**: {v['timeIn']/3600}"),
                Element.Text(f"**击杀**: {v['kills']}"),
                Element.Text(""),
                Element.Text(f"**KPM**: {v['killsPerMinute']}"),
                Element.Text(f"**摧毁**: {v['destroyed']}"),
            ]
        )))

    c.append(Module.Section(
        Element.Text(f"最后更新于{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(d['__update_time']))}")
    ))
    return CardMessage(c)