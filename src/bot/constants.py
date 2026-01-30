from zoneinfo import ZoneInfo

KYIV_TZ = ZoneInfo("Europe/Kyiv")
NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 8
SECS_IN_MINUTE = 60
MINS_IN_HOUR = 60
POWER_SURGE_WARN_MINS = 5
GEN_WORKTIME_SCHEDULE_WEEKDAY = [
    (0, 6 * 60 + 30, False),  # 00:00 - 06:30 break
    (6 * 60 + 30, 10 * 60, True),  # 06:30 - 10:00 working
    (10 * 60, 11 * 60, False),  # 10:00 - 11:00 break
    (11 * 60, 14 * 60, True),  # 11:00 - 14:00 working
    (14 * 60, 15 * 60, False),  # 14:00 - 15:00 break
    (15 * 60, 18 * 60 + 30, True),  # 15:00 - 18:30 working
    (18 * 60 + 30, 19 * 60, False),  # 18:30 - 19:00 break
    (19 * 60, 21 * 60, True),  # 19:00 - 21:00 working
    (21 * 60, 22 * 60, False),  # 21:00 - 22:00 break
    (22 * 60, 24 * 60, True),  # 22:00 - 24:00 working
]

GEN_WORKTIME_SCHEDULE_WEEKEND = [
    (0, 7 * 60, False),  # 00:00 - 07:00 break
    (7 * 60, 10 * 60, True),  # 07:00 - 10:00 working
    (10 * 60, 11 * 60, False),  # 10:00 - 11:00 break
    (11 * 60, 14 * 60, True),  # 11:00 - 14:00 working
    (14 * 60, 15 * 60, False),  # 14:00 - 15:00 break
    (15 * 60, 18 * 60 + 30, True),  # 15:00 - 18:30 working
    (18 * 60 + 30, 19 * 60, False),  # 18:30 - 19:00 break
    (19 * 60, 21 * 60, True),  # 19:00 - 21:00 working
    (21 * 60, 22 * 60, False),  # 21:00 - 22:00 break
    (22 * 60, 24 * 60, True),  # 22:00 - 24:00 working
]
