from decimal import Decimal

from career_insight.data_processing.standardizer import (
    clean_text,
    join_skills,
    normalize_city,
    normalize_education,
    normalize_experience,
    normalize_salary,
    parse_salary_text,
    split_skills,
)


class TestCleanText:
    def test_strips_and_collapses_whitespace(self):
        assert clean_text("  大数据\t开发  ") == "大数据 开发"

    def test_none_returns_default(self):
        assert clean_text(None, "未知") == "未知"

    def test_empty_returns_default(self):
        assert clean_text("   ", "不限") == "不限"


class TestNormalizeCity:
    def test_removes_city_suffix(self):
        assert normalize_city("北京市") == "北京"
        assert normalize_city("香港特别行政区") == "香港"

    def test_keeps_plain_name(self):
        assert normalize_city("杭州") == "杭州"

    def test_empty_is_unknown(self):
        assert normalize_city(None) == "未知"


class TestNormalizeEducation:
    def test_extracts_known_level(self):
        assert normalize_education("本科及以上") == "本科"
        assert normalize_education("硕士优先") == "硕士"

    def test_unlimited(self):
        assert normalize_education("学历不限") == "不限"
        assert normalize_education(None) == "不限"


class TestNormalizeExperience:
    def test_fresh_graduate(self):
        assert normalize_experience("应届毕业生") == "在校/应届"
        assert normalize_experience("实习") == "在校/应届"

    def test_unlimited(self):
        assert normalize_experience("经验不限") == "不限"
        assert normalize_experience(None) == "不限"

    def test_keeps_range(self):
        assert normalize_experience("3-5年") == "3-5年"


class TestParseSalaryText:
    def test_k_range(self):
        assert parse_salary_text("15-25K") == (Decimal("15.00"), Decimal("25.00"))

    def test_wan_monthly(self):
        assert parse_salary_text("1.5-2万") == (Decimal("15.00"), Decimal("20.00"))

    def test_yuan_monthly(self):
        assert parse_salary_text("8000-12000元/月") == (Decimal("8.00"), Decimal("12.00"))

    def test_annual_wan_converted_to_monthly_k(self):
        low, high = parse_salary_text("24-36万/年")
        assert low == Decimal("20.00")
        assert high == Decimal("30.00")

    def test_single_value(self):
        assert parse_salary_text("20K") == (Decimal("20.00"), Decimal("20.00"))

    def test_reversed_range_is_swapped(self):
        assert parse_salary_text("25-15K") == (Decimal("15.00"), Decimal("25.00"))

    def test_negotiable(self):
        assert parse_salary_text("面议") == (None, None)

    def test_empty(self):
        assert parse_salary_text("") == (None, None)


class TestNormalizeSalary:
    def test_uses_existing_values(self):
        low, high, avg = normalize_salary("随便写的", 10, 20)
        assert (low, high, avg) == (Decimal("10.00"), Decimal("20.00"), Decimal("15.00"))

    def test_parses_text_when_values_missing(self):
        low, high, avg = normalize_salary("10-20K")
        assert (low, high, avg) == (Decimal("10.00"), Decimal("20.00"), Decimal("15.00"))

    def test_no_salary_info(self):
        assert normalize_salary("面议") == (None, None, None)


class TestSkills:
    def test_split_normalizes_aliases(self):
        assert split_skills("python,spark/HIVE，sql") == ["Python", "Spark", "Hive", "SQL"]

    def test_split_dedupes_case_insensitive(self):
        assert split_skills("Python,python,PYTHON") == ["Python"]

    def test_split_empty(self):
        assert split_skills(None) == []

    def test_join_round_trip(self):
        assert join_skills(["python", "Spark", "spark"]) == "Python,Spark"
