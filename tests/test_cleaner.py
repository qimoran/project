from decimal import Decimal

from career_insight.data_processing.cleaner import clean_job, clean_jobs


def make_raw(**overrides):
    row = {
        "id": 1,
        "job_title": "大数据开发工程师",
        "company_name": "某科技公司",
        "city": "杭州市",
        "district": "西湖区",
        "salary_text": "15-25K",
        "salary_min": None,
        "salary_max": None,
        "education": "本科及以上",
        "experience": "3-5年",
        "skills": "python,spark,hive",
        "industry": "互联网",
        "source": "zhaopin",
        "source_url": "https://example.com/job/1",
    }
    row.update(overrides)
    return row


class TestCleanJob:
    def test_normalizes_fields(self):
        job = clean_job(make_raw())
        assert job["city"] == "杭州"
        assert job["education"] == "本科"
        assert job["salary_min"] == Decimal("15.00")
        assert job["salary_max"] == Decimal("25.00")
        assert job["salary_avg"] == Decimal("20.00")
        assert job["skills"] == "Python,Spark,Hive"

    def test_missing_title_is_dropped(self):
        assert clean_job(make_raw(job_title="")) is None

    def test_missing_company_is_dropped(self):
        assert clean_job(make_raw(company_name=None)) is None


class TestCleanJobs:
    def test_dedupes_by_source_url(self):
        rows = [
            make_raw(id=1, source_url="https://example.com/job/1"),
            make_raw(id=2, source_url="https://example.com/job/1"),
            make_raw(id=3, source_url="https://example.com/job/3"),
        ]
        cleaned = clean_jobs(rows)
        assert len(cleaned) == 2

    def test_skips_invalid_rows(self):
        rows = [make_raw(), make_raw(id=2, job_title="", source_url="https://example.com/job/2")]
        cleaned = clean_jobs(rows)
        assert len(cleaned) == 1
