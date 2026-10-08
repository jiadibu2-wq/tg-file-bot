"""规则解算引擎：依据命局数据生成解读文字。纯本地计算，结论仅供参考。"""
import datetime

from chart import SHENG, KE

# 生日主的五行（印）
SHENG_TO = {v: k for k, v in SHENG.items()}

DAY_MASTER_TRAITS = {
    "甲": "如参天大树，正直向上、有担当、目标感强，做事有原则；不足处是略显固执、不易低头。",
    "乙": "如藤蔓花草，柔韧善变通、擅长协调与借力，重人情面子；不足处是易随波、决心摇摆。",
    "丙": "如太阳之火，热情开朗、光明磊落、感染力强、行动迅速；不足处是性急、耐性稍欠。",
    "丁": "如灯烛之火，温和细腻、心思缜密、重感情、有奉献精神；不足处是敏感、易多虑。",
    "戊": "如高山厚土，稳重踏实、包容大度、重信用、能扛事；不足处是略保守、变通慢。",
    "己": "如田园之土，温和含蓄、务实包容、善于守成与协调；不足处是易内耗、顾虑较多。",
    "庚": "如刀剑之金，刚毅果断、讲义气、执行力强、遇事敢担当；不足处是过刚易折、言语直接。",
    "辛": "如珠玉之金，精致敏锐、重品味细节、自尊心强、念旧重情；不足处是易钻牛角尖。",
    "壬": "如江河之水，聪明机变、格局开阔、善交际、适应力强；不足处是心思浮动、易漂泊。",
    "癸": "如雨露之水，内敛聪慧、重细节、直觉敏锐、体察入微；不足处是多思多虑、易感伤。",
}

SHI_SHEN_TRAITS = {
    "比肩": "重自我与独立，行动靠自己，朋友同辈助力多，也易有竞争。",
    "劫财": "有冲劲、敢冒险，善交际但需防因朋友、合伙而破财。",
    "食神": "性情温和、有口福才艺，善于表达与享受生活，重品质。",
    "伤官": "才华外显、思维活跃、有创新与表现欲，不喜被约束。",
    "正财": "务实稳健、善于积累，重视稳定的收入与实际保障。",
    "偏财": "机敏、善抓机会财，交际广、出手大方，财来财去较快。",
    "正官": "重责任与规矩，在意外界评价，适合体制或规范化环境。",
    "七杀": "有魄力与抗压性，敢于突破，压力与机遇并存。",
    "正印": "重学识与庇护，心地仁厚、贵人相助，偏稳守。",
    "偏印": "思维专精、灵感强，适合专业领域，但易多疑孤僻。",
}

WUXING_TRAITS = {
    "木": "仁", "火": "礼", "土": "信", "金": "义", "水": "智",
}


def _strength(chart):
    """简易旺衰评估：同党（比劫+印）与异党（食伤+财+官杀）的力量对比。"""
    dm = chart["dayMaster"]["wuXing"]
    score = chart["wuXing"]["score"]
    same_wx = dm                 # 比劫
    sheng_wx = SHENG_TO[dm]      # 印
    ally = score.get(same_wx, 0) + score.get(sheng_wx, 0)
    total = sum(score.values()) or 1.0
    ratio = ally / total

    month_zhi_wx = chart["pillars"]["month"]["zhiWuXing"]
    de_ling = month_zhi_wx in (same_wx, sheng_wx)

    if ratio < 0.35:
        level, desc = "身弱", "日主力量偏弱，宜生扶。"
    elif ratio < 0.45:
        level, desc = "偏弱", "日主力量略弱，喜帮扶。"
    elif ratio <= 0.55:
        level, desc = "中和", "日主力量较为均衡，命局相对平稳。"
    elif ratio <= 0.65:
        level, desc = "偏强", "日主力量略旺，喜适当泄耗。"
    else:
        level, desc = "身强", "日主力量偏旺，宜克泄耗。"

    return {
        "level": level, "desc": desc, "ratio": round(ratio * 100, 1),
        "ally": round(ally, 2), "total": round(total, 2),
        "deLing": de_ling, "sameWx": same_wx, "shengWx": sheng_wx,
    }


def _favorable(chart, st):
    """喜用神启发式：身弱取印比，身强取食伤财官。"""
    dm = chart["dayMaster"]["wuXing"]
    if st["level"] in ("身弱", "偏弱"):
        favor = [SHENG_TO[dm], dm]                 # 印、比劫
        note = "宜以「生扶日主」的五行为用，即印星与比劫。"
    elif st["level"] in ("身强", "偏强"):
        favor = [SHENG[dm], KE[dm], _ke_officer_wx(dm)]  # 食伤、财、官杀
        note = "宜以「泄耗克制日主」的五行为用，即食伤、财星与官杀。"
    else:
        favor = []
        note = "命局接近中和，用神随大运流年变化而定，宜顺其气势。"
    # 去重保序
    seen, out = set(), []
    for f in favor:
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return {"favor": out, "note": note,
            "favorTrait": "、".join(WUXING_TRAITS.get(w, w) for w in out)}


def _ke_officer_wx(dm):
    """克日主的五行（官杀）：找 w 使 KE[w] == dm。"""
    for w, t in KE.items():
        if t == dm:
            return w
    return None


def _shishen_stats(chart):
    stats = {}
    for pos in ["year", "month", "day", "time"]:
        p = chart["pillars"][pos]
        if p.get("shiShenGan") and p["shiShenGan"] not in ("日主(元男/元女)",):
            stats[p["shiShenGan"]] = stats.get(p["shiShenGan"], 0) + 1
        for s in p.get("hideShiShen", []):
            stats[s] = stats.get(s, 0) + 1
    return dict(sorted(stats.items(), key=lambda x: -x[1]))


def interpret(chart):
    dm = chart["dayMaster"]
    st = _strength(chart)
    fav = _favorable(chart, st)
    wx = chart["wuXing"]
    ss = _shishen_stats(chart)

    sections = []

    # 1. 命局总览
    jie = chart.get("jieqi") or {}
    mj = jie.get("monthJie") or {}
    overview = [
        f"日主为「{dm['gan']}」{dm['yinYang']}{dm['wuXing']}，生于{chart['pillars']['month']['zhi']}月"
        + (f"（{mj.get('name')} {mj.get('time')} 后入此月）" if mj else "") + "。",
        f"年柱{chart['pillars']['year']['ganzhi']}、月柱{chart['pillars']['month']['ganzhi']}、"
        f"日柱{chart['pillars']['day']['ganzhi']}、时柱{chart['pillars']['time']['ganzhi']}。",
        f"生肖属{chart['shengXiao']}，{chart['shiChen']}出生。",
    ]
    sections.append({"title": "命局总览", "items": overview})

    # 2. 五行力量
    wu_items = [
        "；".join(f"{k}{wx['score'][k]}({wx['percent'][k]}%)"
                  for k in ["木", "火", "土", "金", "水"]),
        f"最旺为{wx['strongest']}，最弱为{wx['weakest']}。",
    ]
    if wx["missing"]:
        wu_items.append(f"八字中不见「{'、'.join(wx['missing'])}」"
                        f"（仅就天干地支本气而言，藏干中可能有气）。")
    else:
        wu_items.append("五行俱全，天干地支本气中不见明显缺失。")
    sections.append({"title": "五行力量", "items": wu_items})

    # 3. 旺衰与用神
    st_items = [
        f"综合评估：{st['level']}（同党占比约 {st['ratio']}%）。{st['desc']}",
        "月令" + ("生扶日主，属得令，先天根基较好。" if st["deLing"] else "不直接生扶日主，需其他干支助力。"),
    ]
    if fav["favor"]:
        st_items.append(f"参考用神（喜神）五行：{'、'.join(fav['favor'])}，主{fav['favorTrait']}。{fav['note']}")
    else:
        st_items.append(fav["note"])
    st_items.append("提示：旺衰与用神为算法启发式判断，不同流派结论可能存在差异，仅供参照。")
    sections.append({"title": "旺衰与用神", "items": st_items})

    # 4. 性格倾向
    p_items = [f"日主{DAY_MASTER_TRAITS[dm['gan']]}"]
    top = [k for k, v in ss.items() if v >= 2][:3]
    if top:
        p_items.append("命局中较突出的十神：" + "；".join(
            f"{k}——{SHI_SHEN_TRAITS[k].rstrip('。')}" for k in top) + "。")
    else:
        p_items.append("各十神分布较为分散，性格表现会随大运流年与所处环境而变。")
    sections.append({"title": "性格倾向", "items": p_items})

    # 5. 十神分布
    ss_items = ["、".join(f"{k}×{v}" for k, v in ss.items()) or "无"]
    for k, v in list(ss.items())[:2]:
        ss_items.append(f"{k}较旺：{SHI_SHEN_TRAITS[k]}")
    sections.append({"title": "十神分布", "items": ss_items})

    # 6. 大运流年
    cur = next((d for d in chart["dayun"] if d["isCurrent"]), None)
    this_year = datetime.date.today().year
    if cur:
        ln = next((n for n in cur["liuNian"] if n["year"] == this_year), None)
        dy_items = [
            f"当前大运：{cur['ganZhi']}（{cur['startAge']}–{cur['endAge']}岁，"
            f"{cur['startYear']}–{cur['endYear']}年），天干为{cur['shiShenGan']}。",
            f"大运十神提示：{SHI_SHEN_TRAITS.get(cur['shiShenGan'], '')}",
        ]
        if ln:
            dy_items.append(f"今年（{this_year}，{ln['ganZhi']}年）流年天干为{ln['shiShenGan']}，"
                            f"{SHI_SHEN_TRAITS.get(ln['shiShenGan'], '')}")
        sections.append({"title": "当前大运流年", "items": dy_items})
    else:
        sections.append({"title": "大运流年", "items": ["尚未进入大运或已超出所排大运范围。"]})

    sections.append({"title": "说明", "items": [
        "以上内容由本地规则引擎自动生成，属传统命理的统计性经验总结，不构成任何决策依据。",
        "排盘基于节气精确时刻计算，如出生时间在节气交界前后，建议核对出生时间的准确度。",
    ]})

    summary = (f"{chart['pillars']['year']['ganzhi']}年 {chart['pillars']['month']['ganzhi']}月 "
               f"{chart['pillars']['day']['ganzhi']}日 {chart['pillars']['time']['ganzhi']}时，"
               f"日主{dm['gan']}{dm['wuXing']}，命局{st['level']}。")

    return {"sections": sections, "summary": summary,
            "strength": st, "favorable": fav, "shiShenStats": ss}


def to_plain_text(chart, result):
    """把盘面与解读整理为纯文本，供 AI 解读时作为上下文。"""
    lines = [result["summary"], ""]
    p = chart["pillars"]
    lines.append("四柱：")
    for label, key in [("年柱", "year"), ("月柱", "month"), ("日柱", "day"), ("时柱", "time")]:
        q = p[key]
        ss = "日主" if key == "day" else q["shiShenGan"]
        lines.append(f"  {label} {q['ganzhi']}（天干{ss}，地支{q['zhi']}藏"
                     f"{'/'.join(q['hideGan'])}，纳音{q['naYin']}，空亡{q['xunKong']}）")
    lines.append(f"农历：{chart['lunarText']}　生肖：{chart['shengXiao']}　时支：{chart['shiChen']}")
    lines.append(f"胎元：{chart['taiYuan']}　命宫：{chart['mingGong']}　身宫：{chart['shenGong']}")
    wx = chart["wuXing"]
    lines.append("五行力量：" + "、".join(f"{k} {v}%" for k, v in wx["percent"].items()))
    lines.append(f"旺衰：{result['strength']['level']}（同党 {result['strength']['ratio']}%）")
    if result["favorable"]["favor"]:
        lines.append("参考用神五行：" + "、".join(result["favorable"]["favor"]))
    lines.append("")
    lines.append("规则引擎解读：")
    for sec in result["sections"]:
        lines.append(f"【{sec['title']}】")
        for it in sec["items"]:
            lines.append("  - " + it)
    cur = next((d for d in chart["dayun"] if d["isCurrent"]), None)
    if cur:
        lines.append("")
        lines.append(f"当前大运：{cur['ganZhi']}（{cur['startYear']}-{cur['endYear']}年）")
    return "\n".join(lines)