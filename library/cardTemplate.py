import time
from khl.card import CardMessage, Card, Module, Element, Types, Struct
from .util_dict import map_zh_dict
from .utils import zh_trad_to_simp

def service_star_helper(kills: int) -> str:
    stars = kills // 100
    if stars < 50:
        return f'{stars}★'
    elif stars < 100:
        return f'(font){stars}★(font)[success]'
    else:
        return f'(font){stars}★(font)[warning]'

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
            Element.Text(f"*等级*:\n{d['rank']}"),
            Element.Text(f"*游戏时间*:\n{round(d['secondsPlayed']/3600, 2)}小时"),
            Element.Text(f"*击杀*:\n{d['kills']}"),
            Element.Text(f"*死亡*: {d['deaths']}"),
            Element.Text(f"*KD*: {d['killDeath']}"),
            Element.Text(f"*KPM*: {d['killsPerMinute']}"),
            Element.Text(f"*SPM*: {d['scorePerMinute']}"),
            Element.Text(f"*复活*: {d['revives']}"),
            Element.Text(f"*治疗*: {d['heals']}"),
            Element.Text(f"*修理*: {d['repairs']}"),
            Element.Text(f"*命中*: {d['accuracy']}"),
            Element.Text(f"*爆头*: {d['headshots']}"),
            Element.Text(f"*最远爆头*: {d['longestHeadShot']}"),
            Element.Text(f"*胜率*: {d['winPercent']}"),
            Element.Text(f"*最高连杀*: {d['highestKillStreak']}")
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
        c2.append(Module.Section(Element.Text(f"**{zh_trad_to_simp(w['weaponName'])}**")))
        c2.append(Module.Section(Struct.Paragraph(
            3,
            Element.Text(f"*时长*: {round(w['timeEquipped']/3600, 2)}小时"),
            Element.Text(f"*击杀*: {w['kills']}({service_star_helper(w['kills'])})"),
            Element.Text(f"*命中率*: {w['accuracy']}"),
            Element.Text(f"*KPM*: {w['killsPerMinute']}"),
            Element.Text(f"*爆头率*: {w['headshots']}"),
            Element.Text(f"*效率*: {w['hitVKills']}")
        )))

    vehicles = sorted(d['vehicles'], key=lambda k: k['kills'], reverse=True)[0:top_n]
    c3 = Card(
        Module.Section(Element.Text("**载具信息**\n")),
        theme=Types.Theme.SUCCESS, size=Types.Size.LG
    )
    for v in vehicles:
        c3.append(Module.Section(Element.Text(f"**{zh_trad_to_simp(v['vehicleName'])}**")))
        c3.append(Module.Section(Struct.Paragraph(
            3, 
            #Element.Text(f"**{v['vehicleName']}**"),
            #Element.Text(f"**游戏时间**:{round(v['timeIn']/3600, 2)}小时"),
            Element.Text(f"*击杀*: {v['kills']}({service_star_helper(v['kills'])})"),
            #Element.Text(""),
            Element.Text(f"*KPM*: {v['killsPerMinute']}"),
            Element.Text(f"*摧毁*: {v['destroyed']}")
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
        c.append(Module.Section(Element.Text(f"{d[i]['server']}\n{d[i]['matchDate']}\n")))
        c.append(
            Module.Section(Struct.Paragraph(
                3,
                Element.Text(f"模式:{map_zh_dict[d[i]['mode']]}"),
                Element.Text(f"地图:{map_zh_dict[d[i]['map']]}"),
                Element.Text(f"结果:{d[i]['result']}"),
                Element.Text(f"击杀:{d[i]['Kills']}"),
                Element.Text(f"死亡:{d[i]['Deaths']}"),
                Element.Text(f"KD:{d[i]['kd']}"),
                Element.Text(f"时长:{d[i]['duration']}"),
                Element.Text(f"KPM:{d[i]['kpm']}"),
                Element.Text(f"爆头:{d[i]['headshot']}")
                #Element.Text(f"得分:{d[i]['Score']}")
            ))
        )
        c.append(Module.Divider())
    return CardMessage(c)


def render_help_card():
    c = Card(theme=Types.Theme.SUCCESS, size=Types.Size.LG)
    c.append(Module.Header("使用说明"))
    c.append(Module.Divider())
    c.append(Module.Section(Element.Text("**战绩查询**")))
    c.append(Module.Section(Element.Text(
        "1. 查战绩: /stat OriginID\n2. 查最近游戏: /r OriginID\n"+
        "3. 查服务器: /f 服务器关键字\n4. 绑定账号(绑定后查询战绩可省略id): /bind OriginID",
        type=Types.Text.PLAIN
    )))
    c.append(Module.Divider())
    c.append(Module.Section(Element.Text("**服务器管理**")))
    c.append(Module.Section(Element.Text(
        "5. 换图: /map 服务器组名 服务器组内编号 地图关键词\n"+
        "6. 踢人: /kick 服务器组名 服务器组内编号 originid 理由(可省略)\n"+
        "7.挪人: /move 服务器组名 服务器组内编号 originid\n"+
        "8. 封禁玩家: /ban 服务器组名 服务器组内编号 OriginID 理由(可省略), /bana 服务器组名 OriginID 理由(可省略)\n"+
        "9. 解封玩家: /unban 服务器组名 服务器组内编号 OriginID, /unbana 服务器组名 OriginID\n"+
        "10. 添加VIP: /vip 服务器组名 服务器组内编号 OriginID 天数(省略即为永久VIP)\n" +
        "11. 移除VIP: /unvip 服务器组名 服务器组内编号 OriginID\n"+
        "12. 查看现有VIP列表: /viplist 服务器名 服务器组内编号\n"+
        "13. 移除过期VIP: /checkvip 服务器名 服务器组内编号",
        type=Types.Text.PLAIN
    )))
    c.append(Module.Divider())
    c.append(Module.Section(Element.Text("**服务器绑定和权限管理**")))
    c.append(Module.Section(Element.Text(
        "14. 添加服务器组： /group 服务器组名 所有者Kook用户名\n"
        "15. 修改服务器组所有者: /chown 服务器组名 新所有者Kook用户名\n"+
        "16. 删除服务器组： /rmgroup 服务器组名\n"+
        "17. 添加服务器: /server 服务器gameid 服务器组名 服务器组内编号 服管OriginId\n"+
        "18. 删除服务器: /rmserver 服务器组名 服务器组内编号\n"+
        "19. 添加/删除服务器管理员: /admin 服务器组名 Kook用户名, /rmadmin 服务器组名 Kook用户名\n"+
        "20. 添加服管账号: /account OriginID remid sid",
        type=Types.Text.PLAIN
    )))
    c.append(Module.Divider())
    c.append(Module.Section(Element.Text("**其他**")))
    c.append(Module.Section(Element.Text(
        "21. 帮助: /help\n"+
        "22. 关于: /about\n"+
        "23. 随机问候: /hello\n"+
        "24. 涩图: 自己试一下doge",
        type=Types.Text.PLAIN
    )))
    return CardMessage(c)

def render_about_card():
    c = Card(theme=Types.Theme.SUCCESS, size=Types.Size.LG)
    c.append(Module.Header("关于 - bf1bot"))
    c.append(Module.Divider())
    c.append(Module.Section(Element.Text(
        "基于khl.py开发，用于战地1战绩查询、服务器管理的KOOK机器人\n"
        "开发者: [Alexhaoge](https://github.com/Alexhaoge)(OpenBLAS#2162)\n"+
        "项目仓库: [https://github.com/Alexhaoge/Battefield1-Kook-Bot](https://github.com/Alexhaoge/Battefield1-Kook-Bot)\n"+
        "开源协议: GPL-3.0"
    )))
    c.append(Module.Section(Element.Text(
        "数据来源: Battlefield 1, [Battlefield Tracker](https://battlefieldtracker.com/bf1/), [api.gametools.network](https://api.gametools.network/docs)\n"+
        "部分代码参考:\nMag1Catz的[Bf3090bot](https://gitee.com/mag1catz/bf3090bot), [xiaomai-bot](https://github.com/g1331/xiaomai-bot), [BF1ServerTools](https://github.com/CrazyZhang666/BF1ServerTools)\n"+
        "特别鸣谢: [Mag1Catz](https://gitee.com/mag1catz)"
    )))
    return CardMessage(c)