"""天文辅助：均时差(Equation of Time)与真太阳时校正。

真太阳时 = 钟表时间 + 均时差 + (当地经度 - 时区标准经线经度) × 4分钟
中国使用东八区，标准经线为 120°E。
"""
import math

STANDARD_MERIDIAN = 120.0  # 东八区标准经线


def _julian_day(y, m, d, hour_utc=0.0):
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return (math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1))
            + d + b - 1524.5) + hour_utc / 24.0


def equation_of_time_minutes(year, month, day, hour_local=12.0):
    """返回均时差，单位：分钟。正值为日晷快于钟表。

    采用 Meeus《Astronomical Algorithms》第 28 章公式，精度约数秒。
    """
    hour_utc = hour_local - 8.0  # 由北京时换算世界时
    jd = _julian_day(year, month, day, hour_utc)
    t = (jd - 2451545.0) / 36525.0

    l0 = 280.4664567 + 360007.6982779 * t + 0.03032028 * t ** 2 \
        + t ** 3 / 49931.0 - t ** 4 / 15300.0 - t ** 5 / 2000000.0
    l0 = math.radians(l0 % 360.0)

    m = math.radians((357.52911 + 35999.05029 * t - 0.0001537 * t ** 2) % 360.0)
    e = 0.016708634 - 0.000042037 * t - 0.0000001267 * t ** 2

    eps = 23.0 + 26.0 / 60.0 + 21.448 / 3600.0 \
        - (46.815 * t + 0.00059 * t ** 2 - 0.001813 * t ** 3) / 3600.0
    eps = math.radians(eps)

    y = math.tan(eps / 2.0) ** 2
    eq = (y * math.sin(2 * l0)
          - 2 * e * math.sin(m)
          + 4 * e * y * math.sin(m) * math.cos(2 * l0)
          - 0.5 * y * y * math.sin(4 * l0)
          - 1.25 * e * e * math.sin(2 * m))
    return math.degrees(eq) * 4.0


def true_solar_offset_minutes(year, month, day, hour, minute, longitude):
    """返回钟表时间 -> 真太阳时的偏移（分钟）。"""
    eot = equation_of_time_minutes(year, month, day, hour + minute / 60.0)
    lon_corr = (longitude - STANDARD_MERIDIAN) * 4.0
    return eot + lon_corr, eot, lon_corr