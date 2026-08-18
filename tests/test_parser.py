from pathlib import Path
import pytest
from app.ingestion.weworkremotely import WeWorkRemotelySource
from app.ingestion.indeed_rss import IndeedRSSSource
from app.ingestion.base import MarkupDriftError

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_parse_wwr_sample_html():
    source = WeWorkRemotelySource()
    html_path = FIXTURES_DIR / "wwr_sample.html"
    html_content = html_path.read_text(encoding="utf-8")

    jobs = source.parse_html(html_content)

    assert len(jobs) == 2
    assert jobs[0]["title"] == "Senior Backend Engineer"
    assert jobs[0]["company_name"] == "Acme Corp"
    assert "acme-corp-senior-backend-engineer" in jobs[0]["url"]
    assert jobs[1]["title"] == "Lead Python Developer"
    assert jobs[1]["company_name"] == "Globex Inc"


def test_parse_wwr_broken_html_raises_markup_drift():
    source = WeWorkRemotelySource()
    broken_html = "<html><body><div><p>No job listings here at all</p></div></body></html>"

    with pytest.raises(MarkupDriftError, match="markup drift"):
        source.parse_html(broken_html)


def test_parse_indeed_rss_sample_xml():
    source = IndeedRSSSource()
    xml_path = FIXTURES_DIR / "indeed_rss_sample.xml"
    xml_content = xml_path.read_text(encoding="utf-8")

    jobs = source.parse_xml(xml_content)

    assert len(jobs) == 2
    assert jobs[0]["title"] == "Senior Full Stack Developer"
    assert jobs[0]["company_name"] == "TechCorp Solutions"
    assert "viewjob?jk=123456789" in jobs[0]["url"]


def test_parse_indeed_rss_empty_xml_raises_markup_drift():
    source = IndeedRSSSource()
    empty_xml = "<?xml version='1.0'?><rss version='2.0'><channel><title>Empty</title></channel></rss>"

    with pytest.raises(MarkupDriftError, match="0 feed entries"):
        source.parse_xml(empty_xml)
