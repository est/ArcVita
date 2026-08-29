"""Core dates 覆盖：BCE 边界、中文前缀、Wikidata 精度."""
from arcvita.core.dates import (
    coerce_precision,
    in_range,
    parse_iso,
    parse_wikidata_date,
    parse_wikidate,
    year_of,
)


def test_parse_wikidate_bce_day():
    iso, prec = parse_wikidata_date("-0551-09-28T00:00:00Z")
    assert iso == "-551-09-28"
    assert prec == "day"
    iso2, prec2 = parse_wikidate("-551-09-28")
    assert iso2 == "-551-09-28"
    assert prec2 == "day"


def test_parse_wikidate_ce():
    assert parse_wikidata_date("2020-01-01T00:00:00Z") == ("2020-01-01", "day")
    assert parse_wikidata_date("+2020-01") == ("2020-01", "month")
    assert parse_wikidata_date("2020") == ("2020", "year")
    assert parse_wikidata_date("") == (None, None)
    assert parse_wikidata_date(None) == (None, None)


def test_parse_iso_chinese_prefix():
    # 前210 -> -210
    assert parse_iso("前210") == ("-210", "year")
    assert parse_iso("前221") == ("-221", "year")
    # 约-221 -> -221
    assert parse_iso("约-221")[0] == "-221"
    assert parse_iso("约-221")[1] == "year"
    # 约-551-09-28 (BCE 带月日)
    iso, prec = parse_iso("约-551-09-28")
    assert iso == "-551-09-28"
    assert prec == "day"
    # 前259 (秦始皇 birth)
    assert parse_iso("前259") == ("-259", "year")
    # 1405 CE
    assert parse_iso("1405") == ("1405", "year")
    assert parse_iso("1405-07-11") == ("1405-07-11", "day")


def test_parse_iso_bce_month_year():
    assert parse_iso("-0551-09") == ("-551-09", "month")
    assert parse_iso("-221") == ("-221", "year")
    assert parse_iso("约前221") == ("-221", "year")


def test_year_of():
    assert year_of("-551-09-28") == -551
    assert year_of("-221") == -221
    assert year_of("前221") == -221
    assert year_of("约-221") == -221
    assert year_of("2020-01-15") == 2020
    assert year_of("1405") == 1405
    assert year_of(None) is None
    assert year_of("") is None
    assert year_of("?") is None


def test_coerce_precision():
    assert coerce_precision("-551-09-28") == "day"
    assert coerce_precision("2020-01") == "month"
    assert coerce_precision("-221") == "year"
    assert coerce_precision("2020") == "year"
    assert coerce_precision(None) is None
    assert coerce_precision("") is None


def test_in_range_bce():
    # 秦始皇统一六国 -230 ~ -221，事件 -221 在范围内
    assert in_range("-221", "-230", "-221") is True
    assert in_range("-225", "-230", "-221") is True
    assert in_range("-231", "-230", "-221") is False
    # CE
    assert in_range("200", "196", "207") is True
    assert in_range("208", "196", "207") is False
    # None 视为不在范围
    assert in_range(None, "-230", "-221") is False
    assert in_range("-221", None, "-221") is False
    # 跨 BCE/CE (应能比较)
    assert in_range("0", "-10", "10") is True
    assert in_range("-5", "-10", "10") is True


def test_in_range_uses_year_only():
    # 仅比较年份，月日忽略
    assert in_range("-551-09-28", "-551", "-479") is True
    assert in_range("-479-04-11", "-551", "-479") is True
    assert in_range("-480", "-551", "-479") is True
    assert in_range("-478", "-551", "-479") is False


def test_parse_iso_alias():
    # 任务要求的 parse_wikidate 别名
    assert parse_wikidate("2020-01-01") == parse_iso("2020-01-01")
    assert parse_wikidata_date("2020-01-01") == parse_iso("2020-01-01")
