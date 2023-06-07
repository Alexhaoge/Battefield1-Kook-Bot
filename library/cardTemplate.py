import time
from khl.card import CardMessage, Card, Module, Element, Types, Struct

def render_stat_card(d: dict, top_n: int = 3) -> CardMessage:
    """
    Render card message for /stat
    """
    c1 = Card(
        Module.Header(f"战地1统计数据 - [{d['activePlatoon']['tag']}]{d['userName']}"),
        Module.Divider(),
        Module.Section(Element.Text("**基本数据**\n")),
        Module.Section(Struct.Paragraph(
            3,
            Element.Text(f"**等级**: {d['rank']}"),
            Element.Text(f"**游戏时间**: {round(d['secondsPlayed']/3600, 2)}"),
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
            Element.Text(f"**最远爆头**: {d['longestHeadShot']}"),
            Element.Text(f"**胜率**: {d['winPercent']}"),
            Element.Text(f"**最高连杀**: {d['highestKillStreak']}")
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
            Element.Text(f"**游戏时间**: {round(w['timeEquipped']/3600, 2)}"),
            Element.Text(f"**击杀**: {w['kills']}"),
            Element.Text(f"**命中**: {w['accuracy']}"),
            Element.Text(f"**KPM**: {w['killsPerMinute']}"),
            Element.Text(f"**爆头**: {w['headshotKills']}"),
            Element.Text(f"**爆头率**: {w['headshots']}"),
            Element.Text(f"**效率**: {w['hitVKills']}")
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
            Element.Text(f"**游戏时间**: {round(v['timeIn']/3600, 2)}"),
            Element.Text(f"**击杀**: {v['kills']}"),
            Element.Text(""),
            Element.Text(f"**KPM**: {v['killsPerMinute']}"),
            Element.Text(f"**摧毁**: {v['destroyed']}")
        )))
    print(Card)

    return CardMessage(c1, c2, c3)