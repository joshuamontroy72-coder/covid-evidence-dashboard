"""
COVID-19 Evidence Watch — data fetchers.

Each fetcher returns a list of record dicts with at minimum:
  id, title, url, source, source_type, published_date
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

from config import (
    ALTMETRIC_API, EUROPMC_API, CLINICALTRIALS_API,
    TIMEOUT, MAX_PER_FETCHER,
)

log = logging.getLogger(__name__)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "COVID-Evidence-Watch/1.0 (kelsey.young@phac-aspc.gc.ca)"})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uid(*parts: str) -> str:
    return hashlib.md5("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def _get(url: str, params: dict | None = None, **kw) -> requests.Response | None:
    try:
        r = SESSION.get(url, params=params, timeout=TIMEOUT, **kw)
        r.raise_for_status()
        return r
    except Exception as exc:
        log.warning("GET %s failed: %s", url, exc)
        return None


def _parse_date(s: str | None) -> str:
    """Normalise any date string to YYYY-MM-DD; fall back to today."""
    if not s:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y", "%d %b %Y", "%b %Y"):
        try:
            return datetime.strptime(s.strip()[:10], fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# 1. Europe PMC — peer-reviewed journals
# ---------------------------------------------------------------------------

_EUROPMC_QUERIES = [
    # Core vaccine policy/effectiveness queries
    '(COVID-19 OR "SARS-CoV-2") AND (vaccine OR vaccination OR immunization) AND (recommendation OR guideline OR policy OR booster OR effectiveness OR efficacy OR safety) AND (SRC:MED OR SRC:PMC)',
    # Population targeting
    '(COVID-19 OR "SARS-CoV-2") AND vaccin* AND ("older adults" OR elderly OR immunocompromised OR "high risk" OR "priority group" OR "healthcare worker") AND (SRC:MED OR SRC:PMC)',
    # Strain / variant focus
    '(COVID-19 OR "SARS-CoV-2") AND vaccin* AND (XBB OR "JN.1" OR "KP.2" OR bivalent OR monovalent OR "updated vaccine" OR "variant-adapted") AND (SRC:MED OR SRC:PMC)',
    # Booster timing
    '(COVID-19 OR "SARS-CoV-2") AND vaccin* AND ("waning immunity" OR "dose interval" OR "booster timing" OR "annual" OR "seasonal") AND (SRC:MED OR SRC:PMC)',
]


def fetch_europmc_journals() -> list[dict]:
    records = []
    seen: set[str] = set()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365 * 3)).strftime("%Y-%m-%d")

    for query in _EUROPMC_QUERIES:
        params = {
            "query":       query,
            "format":      "json",
            "pageSize":    50,
            "sort":        "P_PDATE_D desc",
            "resultType":  "core",
            "fromDate":    cutoff,
            "source":      "MED,PMC",
        }
        r = _get(EUROPMC_API, params=params)
        if not r:
            continue
        data = r.json()
        for art in data.get("resultList", {}).get("result", []):
            pmid = art.get("pmid") or art.get("id", "")
            uid  = f"pubmed_{pmid}" if pmid else f"epmc_{_uid(art.get('title',''))}"
            if uid in seen:
                continue
            seen.add(uid)

            # Build authors string
            authors = ""
            auth_list = art.get("authorList", {}).get("author", [])
            if auth_list:
                names = [f"{a.get('lastName', '')} {a.get('initials', '')}".strip() for a in auth_list[:3]]
                authors = ", ".join(n for n in names if n)
                if len(auth_list) > 3:
                    authors += " et al."

            pub_date = art.get("firstPublicationDate") or art.get("pubYear") or ""

            records.append({
                "id":             uid,
                "title":          art.get("title", "").rstrip("."),
                "authors":        authors,
                "journal":        art.get("journalTitle") or art.get("journalAbbreviation", ""),
                "published_date": _parse_date(pub_date),
                "url":            f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else art.get("fullTextUrlList", {}).get("fullTextUrl", [{}])[0].get("url", ""),
                "source":         "PubMed / Europe PMC",
                "source_type":    "journal_article",
                "pmid":           str(pmid) if pmid else "",
                "summary":        (art.get("abstractText") or "")[:600],
            })
            if len(records) >= MAX_PER_FETCHER:
                return records
    return records


# ---------------------------------------------------------------------------
# 2. Europe PMC — preprints (medRxiv / bioRxiv)
# ---------------------------------------------------------------------------

def fetch_preprints() -> list[dict]:
    records = []
    seen: set[str] = set()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y-%m-%d")

    query = (
        '(COVID-19 OR "SARS-CoV-2") AND vaccin* AND '
        '(booster OR effectiveness OR safety OR recommendation OR strain OR variant OR "population targeting") '
        'AND (SRC:PPR)'
    )
    params = {
        "query":      query,
        "format":     "json",
        "pageSize":   80,
        "sort":       "P_PDATE_D desc",
        "resultType": "core",
        "fromDate":   cutoff,
    }
    r = _get(EUROPMC_API, params=params)
    if not r:
        return []

    for art in r.json().get("resultList", {}).get("result", []):
        pid  = art.get("id", "")
        uid  = f"preprint_{pid}" if pid else f"ppr_{_uid(art.get('title',''))}"
        if uid in seen:
            continue
        seen.add(uid)

        auth_list = art.get("authorList", {}).get("author", [])
        authors   = ""
        if auth_list:
            names   = [f"{a.get('lastName','')} {a.get('initials','')}".strip() for a in auth_list[:3]]
            authors = ", ".join(n for n in names if n)
            if len(auth_list) > 3:
                authors += " et al."

        server = art.get("bookOrReportDetails", {}).get("publisher", "") or "medRxiv/bioRxiv"
        url    = ""
        for u in art.get("fullTextUrlList", {}).get("fullTextUrl", []):
            if u.get("documentStyle") == "html":
                url = u["url"]
                break
        if not url and pid:
            url = f"https://europepmc.org/article/PPR/{pid}"

        records.append({
            "id":             uid,
            "title":          art.get("title", "").rstrip("."),
            "authors":        authors,
            "journal":        server,
            "published_date": _parse_date(art.get("firstPublicationDate") or art.get("pubYear")),
            "url":            url,
            "source":         "medRxiv / bioRxiv",
            "source_type":    "preprint",
            "summary":        (art.get("abstractText") or "")[:600],
        })
    return records


# ---------------------------------------------------------------------------
# 3. ClinicalTrials.gov — COVID vaccine trials
# ---------------------------------------------------------------------------

def fetch_clinical_trials() -> list[dict]:
    params = {
        "query.cond":     "COVID-19",
        "query.intr":     "vaccine",
        "filter.overallStatus": "RECRUITING,ACTIVE_NOT_RECRUITING,COMPLETED",
        "fields":         "NCTId,BriefTitle,OfficialTitle,BriefSummary,StartDate,PrimaryCompletionDate,OverallStatus,Phase,EnrollmentCount,LeadSponsorName",
        "pageSize":       80,
        "sort":           "LastUpdatePostDate:desc",
        "format":         "json",
    }
    r = _get(CLINICALTRIALS_API, params=params)
    if not r:
        return []

    records = []
    for study in r.json().get("studies", []):
        proto = study.get("protocolSection", {})
        ident = proto.get("identificationModule", {})
        desc  = proto.get("descriptionModule", {})
        stat  = proto.get("statusModule", {})
        design = proto.get("designModule", {})
        sponsor = proto.get("sponsorCollaboratorsModule", {})

        nct_id   = ident.get("nctId", "")
        title    = ident.get("briefTitle") or ident.get("officialTitle", "")
        summary  = desc.get("briefSummary", "")[:600]
        phase    = ", ".join(design.get("phases", [])) if design.get("phases") else ""
        sponsor_name = sponsor.get("leadSponsor", {}).get("name", "")
        start    = stat.get("startDateStruct", {}).get("date", "")
        status   = stat.get("overallStatus", "")

        records.append({
            "id":             f"ct_{nct_id}",
            "title":          title,
            "authors":        sponsor_name,
            "journal":        f"ClinicalTrials.gov · {phase}" if phase else "ClinicalTrials.gov",
            "published_date": _parse_date(start),
            "url":            f"https://clinicaltrials.gov/study/{nct_id}",
            "source":         "ClinicalTrials.gov",
            "source_type":    "clinical_trial",
            "summary":        summary,
            "extra":          {"nct_id": nct_id, "status": status, "phase": phase},
        })
    return records


# ---------------------------------------------------------------------------
# 4. WHO IRIS — COVID-19 vaccine documents
# ---------------------------------------------------------------------------

_WHO_IRIS_QUERIES = [
    "COVID-19 vaccine recommendation",
    "SARS-CoV-2 vaccine SAGE",
    "COVID-19 immunization guidance",
]


def fetch_who_iris() -> list[dict]:
    records = []
    seen: set[str] = set()

    for q in _WHO_IRIS_QUERIES:
        r = _get(
            "https://iris.who.int/rest/items/find-by-metadata-field",
            params={"metadataField": "dc.subject", "metadataValue": q,
                    "limit": 30, "offset": 0},
        )
        if not r:
            # Fallback: WHO IRIS search endpoint
            r = _get(
                "https://iris.who.int/rest/discover/search/objects",
                params={"query": q, "dsoTypes": "item", "size": 30,
                        "sort": "dc.date.issued,DESC"},
            )
        if not r:
            continue

        # Try to parse whatever we got
        try:
            data = r.json()
            items = (
                data.get("_embedded", {}).get("searchResult", {})
                    .get("_embedded", {}).get("objects", [])
                or data.get("_embedded", {}).get("objects", [])
                or (data if isinstance(data, list) else [])
            )
        except Exception:
            continue

        for item in items:
            meta = {}
            for m in item.get("metadata", []) if isinstance(item.get("metadata"), list) else []:
                k = m.get("key", "")
                if k not in meta:
                    meta[k] = m.get("value", "")

            handle = item.get("handle", "")
            url    = f"https://iris.who.int/handle/{handle}" if handle else ""
            title  = meta.get("dc.title", item.get("name", ""))
            date   = meta.get("dc.date.issued", "")
            uid    = f"who_{handle.replace('/', '_')}" if handle else f"who_{_uid(title)}"

            if uid in seen or not title:
                continue
            seen.add(uid)

            records.append({
                "id":             uid,
                "title":          title,
                "authors":        meta.get("dc.creator", "WHO"),
                "journal":        "WHO IRIS",
                "published_date": _parse_date(date),
                "url":            url,
                "source":         "WHO IRIS",
                "source_type":    "guideline",
                "summary":        meta.get("dc.description.abstract", "")[:600],
                "extra":          {"sage": True},
            })
    return records


# ---------------------------------------------------------------------------
# 5. RSS feeds — NACI, ACIP, ECDC, JCVI, PHO
# ---------------------------------------------------------------------------

_RSS_FEEDS: list[tuple[str, str, str, str]] = [
    # (label, url, source, source_type)
    (
        "PHAC / NACI (Canada.ca)",
        "https://www.canada.ca/en/public-health/services/immunization/national-advisory-committee-on-immunization-naci.atom",
        "NACI / PHAC",
        "guideline",
    ),
    (
        "PHAC COVID updates",
        "https://www.canada.ca/en/public-health/news/2024.atom",
        "PHAC",
        "guideline",
    ),
    (
        "CDC ACIP",
        "https://www.cdc.gov/rss/acip.xml",
        "CDC ACIP",
        "guideline",
    ),
    (
        "CDC COVID Vaccines",
        "https://tools.cdc.gov/api/v2/resources/media/404952.rss",
        "CDC",
        "guideline",
    ),
    (
        "ECDC COVID-19 vaccine",
        "https://www.ecdc.europa.eu/en/rss-feeds/covid-19-vaccine-updates",
        "ECDC",
        "guideline",
    ),
    (
        "ECDC Technical guidance",
        "https://www.ecdc.europa.eu/en/rss-feeds/technical-guidance",
        "ECDC",
        "surveillance",
    ),
    (
        "Public Health Ontario",
        "https://www.publichealthontario.ca/en/rss/reports",
        "Public Health Ontario",
        "surveillance",
    ),
    (
        "WHO COVID news",
        "https://www.who.int/rss-feeds/news-english.xml",
        "WHO",
        "guideline",
    ),
    (
        "UK UKHSA",
        "https://www.gov.uk/search/all.atom?keywords=covid+vaccine+recommendation&order=updated-newest&organisations[]=uk-health-security-agency",
        "UKHSA",
        "guideline",
    ),
    (
        "Australia ATAGI",
        "https://www.health.gov.au/rss.xml",
        "ATAGI / Australia DoH",
        "guideline",
    ),
]


def fetch_rss_feeds() -> list[dict]:
    try:
        import feedparser
    except ImportError:
        log.warning("feedparser not installed — skipping RSS feeds")
        return []

    records = []
    seen: set[str] = set()

    for label, feed_url, source, source_type in _RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
        except Exception as exc:
            log.warning("RSS %s failed: %s", label, exc)
            continue

        for entry in feed.entries[:40]:
            link  = entry.get("link", "")
            title = entry.get("title", "").strip()
            uid   = f"rss_{_uid(link or title)}"
            if uid in seen or not title:
                continue
            seen.add(uid)

            # Extract date
            pub = entry.get("published") or entry.get("updated") or ""
            try:
                from email.utils import parsedate_to_datetime
                dt = parsedate_to_datetime(pub)
                pub_date = dt.strftime("%Y-%m-%d")
            except Exception:
                pub_date = _parse_date(pub[:10] if pub else "")

            summary = entry.get("summary", "").strip()
            # Strip HTML tags from summary
            import re
            summary = re.sub(r"<[^>]+>", " ", summary).strip()[:600]

            records.append({
                "id":             uid,
                "title":          title,
                "authors":        source,
                "journal":        source,
                "published_date": pub_date,
                "url":            link,
                "source":         source,
                "source_type":    source_type,
                "summary":        summary,
            })

    return records


# ---------------------------------------------------------------------------
# 6. Google News — COVID vaccine policy news
# ---------------------------------------------------------------------------

_NEWS_QUERIES = [
    "COVID-19 vaccine recommendation updated",
    "COVID booster recommendation NACI 2024 2025",
    "WHO SAGE COVID vaccine guidance",
    "COVID vaccine booster who should get",
    "COVID-19 vaccine policy change",
    "COVID vaccine fall campaign 2025",
]


def fetch_google_news() -> list[dict]:
    try:
        import feedparser
    except ImportError:
        return []

    records = []
    seen: set[str] = set()

    for q in _NEWS_QUERIES:
        encoded = requests.utils.quote(q)
        url     = f"https://news.google.com/rss/search?q={encoded}&hl=en-CA&gl=CA&ceid=CA:en"
        try:
            import feedparser
            feed = feedparser.parse(url)
        except Exception:
            continue

        for entry in feed.entries[:15]:
            link  = entry.get("link", "")
            title = entry.get("title", "").strip()
            uid   = f"news_{_uid(link or title)}"
            if uid in seen or not title:
                continue
            seen.add(uid)

            pub = entry.get("published", "")
            try:
                from email.utils import parsedate_to_datetime
                pub_date = parsedate_to_datetime(pub).strftime("%Y-%m-%d")
            except Exception:
                pub_date = _parse_date(pub[:10] if pub else "")

            import re
            summary = re.sub(r"<[^>]+>", " ", entry.get("summary", "")).strip()[:400]

            records.append({
                "id":             uid,
                "title":          title,
                "authors":        entry.get("source", {}).get("title", ""),
                "journal":        entry.get("source", {}).get("title", "News"),
                "published_date": pub_date,
                "url":            link,
                "source":         "Google News",
                "source_type":    "news",
                "summary":        summary,
            })

    return records


# ---------------------------------------------------------------------------
# 7. Altmetric enrichment
# ---------------------------------------------------------------------------

def enrich_altmetric(records: list[dict]) -> None:
    """Add altmetric_score to records that have a PMID. In-place."""
    api_key = os.environ.get("ALTMETRIC_KEY", "")
    for rec in records:
        pmid = rec.get("pmid")
        if not pmid:
            continue
        url = ALTMETRIC_API.format(pmid=pmid)
        if api_key:
            url += f"?key={api_key}"
        r = _get(url)
        if r:
            try:
                rec["altmetric_score"] = r.json().get("score", 0)
            except Exception:
                pass
        time.sleep(0.5)  # rate-limit


# ---------------------------------------------------------------------------
# All fetchers — imported by update.py
# ---------------------------------------------------------------------------

ALL_FETCHERS: list[tuple[str, Any]] = [
    ("Europe PMC (journals)",     fetch_europmc_journals),
    ("medRxiv / bioRxiv preprints", fetch_preprints),
    ("ClinicalTrials.gov",        fetch_clinical_trials),
    ("WHO IRIS",                  fetch_who_iris),
    ("RSS feeds (NACI/ACIP/ECDC/PHO/WHO)", fetch_rss_feeds),
    ("Google News",               fetch_google_news),
]
