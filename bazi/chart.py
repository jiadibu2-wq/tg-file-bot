"""排盘核心：基于 lunar-python（寿星天文历算法）计算四柱、十神、藏干、大运、流年等。

所有计算在本机完成，不发起任何网络请求。
"""
import datetime

from lunar_python import Solar, Lunar

# ---------- 基础映射 ----------

GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"

WU_XING_GAN = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
               "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
WU_XING_ZHI = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
               "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}

ZHI_HIDE_GAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"],
    "卯": ["乙"], "辰": ["戊", "乙", "癸"], "巳": ["丙", "庚", "戊"],
    "午": ["丁", "己"], "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"],
    "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}
# 藏干权重：本气 / 中气 / 余气
HIDE_WEIGHT = {0: 1.0, 1: 0.5, 2: 0.3}

SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}   # 我生
KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}       # 我克

SHI_SHEN_NAMES = {
    "同-同": "比肩", "同-异": "劫财",
    "生-同": "食神", "生-异": "伤官",
    "克-同": "偏财", "克-异": "正财",
    "被克-同": "七杀", "被克-异": "正官",
    "被生-同": "偏印", "被生-异": "正印",
}


def is_yang(gan):
    return GAN.index(gan) % 2 == 0


def shi_shen(day_gan, target_gan):
    """以日主为参照，求 target_gan 的十神。"""
    if not target_gan:
        return ""
    d_wx, t_wx = WU_XING_GAN[day_gan], WU_XING_GAN[target_gan]
    if d_wx == t_wx:
        rel = "同"
    elif SHENG[d_wx] == t_wx:
        rel = "生"        # 日主生它 -> 食伤
    elif KE[d_wx] == t_wx:
        rel = "克"        # 日主克它 -> 财
    elif KE[t_wx] == d_wx:
        rel = "被克"      # 它克日主 -> 官杀
    else:
        rel = "被生"      # 它生日主 -> 印
    same = "同" if is_yang(day_gan) == is_yang(target_gan) else "异"
    return SHI_SHEN_NAMES[f"{rel}-{same}"]


# ---------- 主入口 ----------

def build_chart(inp):
    """inp: dict(name, gender, calendar, year, month, day, hour, minute,
                is_leap, longitude, use_true_solar, sect, note)"""
    cal = inp.get("calendar", "solar")
    y, m, d = int(inp["year"]), int(inp["month"]), int(inp["day"])
    hh, mi = int(inp.get("hour", 0)), int(inp.get("minute", 0))
    sect = int(inp.get("sect", 2))

    # 1) 取基础公历时间
    if cal == "lunar":
        lm = -m if inp.get("is_leap") else m
        lunar_in = Lunar.fromYmdHms(y, lm, d, hh, mi, 0)
        solar = lunar_in.getSolar()
    else:
        solar = Solar.fromYmdHms(y, m, d, hh, mi, 0)

    # 2) 真太阳时校正（可选）
    true_solar_info = None
    if inp.get("use_true_solar") and inp.get("longitude") is not None:
        from astro import true_solar_offset_minutes
        offset, eot, lon_corr = true_solar_offset_minutes(
            solar.getYear(), solar.getMonth(), solar.getDay(),
            solar.getHour(), solar.getMinute(), float(inp["longitude"]))
        base = datetime.datetime(solar.getYear(), solar.getMonth(), solar.getDay(),
                                 solar.getHour(), solar.getMinute())
        adj = base + datetime.timedelta(minutes=offset)
        solar = Solar.fromYmdHms(adj.year, adj.month, adj.day, adj.hour, adj.minute, 0)
        true_solar_info = {
            "longitude": float(inp["longitude"]),
            "offsetMinutes": round(offset, 1),
            "equationOfTime": round(eot, 1),
            "longitudeCorrection": round(lon_corr, 1),
            "trueSolarTime": adj.strftime("%Y-%m-%d %H:%M"),
        }

    lunar = solar.getLunar()
    ec = lunar.getEightChar()
    try:
        # 晚子时(23:00-24:00)流派：1=日柱算次日，2=日柱算当天
        ec.setSect(sect)
    except Exception:
        pass

    day_gan = ec.getDayGan()

    def pillar(gan, zhi, pos):
        hide = ZHI_HIDE_GAN.get(zhi, [])
        return {
            "gan": gan, "zhi": zhi, "ganzhi": gan + zhi,
            "ganWuXing": WU_XING_GAN[gan], "zhiWuXing": WU_XING_ZHI[zhi],
            "shiShenGan": "" if pos == "day" else shi_shen(day_gan, gan),
            "hideGan": hide,
            "hideShiShen": [shi_shen(day_gan, g) for g in hide],
        }

    pillars = {
        "year": pillar(ec.getYearGan(), ec.getYearZhi(), "year"),
        "month": pillar(ec.getMonthGan(), ec.getMonthZhi(), "month"),
        "day": pillar(ec.getDayGan(), ec.getDayZhi(), "day"),
        "time": pillar(ec.getTimeGan(), ec.getTimeZhi(), "time"),
    }
    pillars["year"]["naYin"] = ec.getYearNaYin()
    pillars["month"]["naYin"] = ec.getMonthNaYin()
    pillars["day"]["naYin"] = ec.getDayNaYin()
    pillars["time"]["naYin"] = ec.getTimeNaYin()
    pillars["year"]["xunKong"] = ec.getYearXunKong()
    pillars["month"]["xunKong"] = ec.getMonthXunKong()
    pillars["day"]["xunKong"] = ec.getDayXunKong()
    pillars["time"]["xunKong"] = ec.getTimeXunKong()
    pillars["day"]["shiShenGan"] = "日主(元男/元女)"

    # 3) 五行统计
    wuxing = _count_wuxing(pillars)

    # 4) 大运 / 流年
    gender = int(inp.get("gender", 1))
    yun = ec.getYun(1 if gender == 1 else 0)
    now_year = datetime.date.today().year

    dayun_list = []
    for dy in yun.getDaYun():
        if dy.getIndex() == 0:      # 童限，无干支
            continue
        gz = dy.getGanZhi()
        item = {
            "ganZhi": gz,
            "gan": gz[0], "zhi": gz[1],
            "shiShenGan": shi_shen(day_gan, gz[0]),
            "shiShenZhi": shi_shen(day_gan, ZHI_HIDE_GAN.get(gz[1], ["_"])[0]),
            "startAge": dy.getStartAge(), "endAge": dy.getEndAge(),
            "startYear": dy.getStartYear(), "endYear": dy.getEndYear(),
            "isCurrent": dy.getStartYear() <= now_year <= dy.getEndYear(),
            "liuNian": [{"year": n.getYear(), "age": n.getAge(), "ganZhi": n.getGanZhi(),
                         "shiShenGan": shi_shen(day_gan, n.getGanZhi()[0])}
                        for n in dy.getLiuNian()],
        }
        dayun_list.append(item)

    qiyun = {
        "text": f"出生后约 {yun.getStartYear()} 年 {yun.getStartMonth()} 个月 "
                f"{yun.getStartDay()} 天起运",
        "startYear": yun.getStartYear(), "startMonth": yun.getStartMonth(),
        "startDay": yun.getStartDay(),
    }

    # 5) 节气（月柱边界）
    jieqi = _jieqi_info(lunar, ec.getMonthZhi())

    chart = {
        "input": {
            "name": inp.get("name") or "未命名",
            "gender": gender,
            "genderText": "男" if gender == 1 else "女",
            "calendar": cal,
            "note": inp.get("note") or "",
        },
        "solar": {
            "datetime": "%04d-%02d-%02d %02d:%02d" % (
                solar.getYear(), solar.getMonth(), solar.getDay(),
                solar.getHour(), solar.getMinute()),
            "year": solar.getYear(),
        },
        "trueSolar": true_solar_info,
        "lunarText": lunar.toString(),
        "lunarYmd": "%d年%d月%d日" % (lunar.getYear(), lunar.getMonth(), lunar.getDay()),
        "shengXiao": lunar.getYearShengXiao(),
        "shiChen": ec.getTimeZhi() + "时",
        "dayMaster": {"gan": day_gan, "wuXing": WU_XING_GAN[day_gan],
                      "yinYang": "阳" if is_yang(day_gan) else "阴"},
        "pillars": pillars,
        "wuXing": wuxing,
        "taiYuan": ec.getTaiYuan(),
        "mingGong": ec.getMingGong(),
        "shenGong": ec.getShenGong(),
        "naYinDay": ec.getDayNaYin(),
        "qiyun": qiyun,
        "dayun": dayun_list,
        "jieqi": jieqi,
    }
    return chart


def _count_wuxing(pillars):
    """统计五行力量：天干 1.0；地支本气 1.2（月支加倍）；中气 0.5；余气 0.3。"""
    score = {k: 0.0 for k in ["木", "火", "土", "金", "水"]}
    count = {k: 0 for k in ["木", "火", "土", "金", "水"]}

    for pos in ["year", "month", "day", "time"]:
        p = pillars[pos]
        score[p["ganWuXing"]] += 1.0
        count[p["ganWuXing"]] += 1
        zhi = p["zhi"]
        for i, g in enumerate(ZHI_HIDE_GAN.get(zhi, [])):
            w = HIDE_WEIGHT.get(i, 0.3)
            if pos == "month" and i == 0:
                w *= 2.0      # 月令得气，权重加倍
            score[WU_XING_GAN[g]] += w
        count[p["zhiWuXing"]] += 1

    total = sum(score.values()) or 1.0
    return {
        "score": {k: round(v, 2) for k, v in score.items()},
        "percent": {k: round(v * 100 / total, 1) for k, v in score.items()},
        "count": count,
        "missing": [k for k, v in count.items() if v == 0],
        "strongest": max(score, key=score.get),
        "weakest": min(score, key=score.get),
    }


def _jieqi_info(lunar, month_zhi):
    """定位月柱所属的「节」（节气中的节）及其精确时刻，用于说明换月边界。"""
    out = {"monthJie": None, "nextJie": None, "liChun": None}
    try:
        pj = lunar.getPrevJie(False)   # wholeDay=False，按精确时刻判定
        out["monthJie"] = {"name": pj.getName(), "time": pj.getSolar().toYmdHms(),
                           "zhi": month_zhi}
        nj = lunar.getNextJie(False)
        out["nextJie"] = {"name": nj.getName(), "time": nj.getSolar().toYmdHms()}
    except Exception:
        pass
    try:
        out["liChun"] = lunar.getJieQiTable()["立春"].toYmdHms()
    except Exception:
        pass
    return out