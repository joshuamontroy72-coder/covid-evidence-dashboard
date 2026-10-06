"""
COVID-19 Evidence Watch — classification module.

Assigns each record:
  - policy_area / policy_area_labels (list)
  - pregnancy_related (bool)
  - canadian (bool)
  - species ("human" | "animal")
"""
from __future__ import annotations

POLICY_AREA_LABELS: dict[str, str] = {
    "booster_frequency":    "Booster frequency & intervals",
    "population_targeting": "Population targeting",
    "strain_selection":     "Vaccine strain selection",
    "general_covid":        "General COVID-19 vaccines",
}

# ---------------------------------------------------------------------------
# Keyword lists
# ---------------------------------------------------------------------------

_BOOSTER_KW = [
    "booster", "additional dose", "fourth dose", "fifth dose", "sixth dose",
    "dose interval", "dosing interval", "inter-dose", "timing",
    "annual", "biannual", "semi-annual", "seasonal", "fall campaign",
    "autumn campaign", "primary series", "waning immunity", "waning protection",
    "protection duration", "durability", "second booster", "updated dose",
    "repeat vaccination", "revaccination", "hybrid immunity",
    "frequency of vaccination", "how often",
]

_POPULATION_KW = [
    "elderly", "older adult", "65 year", "60 year", "75 year", "80 year",
    "senior", "aged", "frail", "long-term care", "nursing home", "care home",
    "immunocompromised", "immunosuppressed", "immunodeficien",
    "solid organ transplant", "hematopoietic", "hematologic", "stem cell",
    "cancer", "malignancy", "chemotherapy", "biological therapy",
    "autoimmune", "inflammatory", "rheumatoid", "lupus", "crohn",
    "high risk", "high-risk", "at-risk", "risk group", "priority group",
    "vulnerable population", "clinically vulnerable",
    "healthcare worker", "health care worker", "hcw", "frontline",
    "pregnant", "pregnancy", "maternal", "perinatal", "postpartum",
    "breastfeed", "lactati",
    "children", "pediatric", "paediatric", "adolescent",
    "young adult", "adult under", "general population",
]

_STRAIN_KW = [
    "xbb", "jn.1", "jn1", "kp.2", "kp2", "kp.1", "kp1", "xec", "lp.8",
    "ba.2", "ba.4", "ba.5", "ba.2.86", "pirola",
    "omicron", "delta", "variant of concern", "variant of interest",
    "bivalent", "monovalent", "trivalent", "updated formula",
    "strain selection", "strain composition", "antigen composition",
    "variant-adapted", "variant adapted", "reformulated", "updated vaccine",
    "new formula", "ancestral strain", "wuhan strain",
    "subvariant", "sublineage", "recombinant variant",
    "immune escape", "neutralization", "cross-reactive",
]

_PREGNANCY_KW = [
    "pregnan", "maternal", "perinatal", "obstetric", "antenatal", "prenatal",
    "trimester", "gestational", "postpartum", "breast feed", "breastfeed",
    "lactati", "neonatal", "newborn", "infant", "fetus", "fetal", "placenta",
]

_CANADIAN_KW = [
    "canada", "canadian", "naci", "phac", "ontario", "quebec", "québec",
    "british columbia", "alberta", "manitoba", "saskatchewan",
    "nova scotia", "new brunswick", "newfoundland", "pei", "prince edward",
    "yukon", "northwest territories", "nunavut", "ccdr",
    "provincial", "territorial",
]

_CANADIAN_DOMAINS = {
    "canada.ca", "phac-aspc.gc.ca", "gov.on.ca",
    "publichealthontario.ca", "bccdc.ca", "gov.bc.ca",
    "alberta.ca", "gov.ab.ca", "gov.mb.ca", "gov.sk.ca",
    "novascotia.ca", "gnb.ca", "gov.nl.ca", "pei.ca",
}

_ANIMAL_KW = [
    "mouse", "mice", "rat ", "rats ", "hamster", "primate",
    "macaque", "ferret", "in vitro", "cell line", "murine",
    "animal model", "preclinical",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _hay(rec: dict) -> str:
    return " ".join(filter(None, [
        rec.get("title", ""),
        rec.get("summary", ""),
        rec.get("abstract", ""),
        rec.get("journal", ""),
        rec.get("source", ""),
        rec.get("authors", ""),
    ])).lower()


def _url_host(rec: dict) -> str:
    try:
        from urllib.parse import urlparse
        return urlparse(rec.get("url", "")).hostname or ""
    except Exception:
        return ""


def _match(hay: str, kws: list[str]) -> bool:
    return any(k in hay for k in kws)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(rec: dict) -> dict:
    """Assign policy_area, flags, and species to a record (in-place)."""
    hay  = _hay(rec)
    host = _url_host(rec)

    areas: list[str] = []
    if _match(hay, _BOOSTER_KW):
        areas.append("booster_frequency")
    if _match(hay, _POPULATION_KW):
        areas.append("population_targeting")
    if _match(hay, _STRAIN_KW):
        areas.append("strain_selection")
    if not areas:
        areas = ["general_covid"]

    rec["policy_area"]        = areas
    rec["policy_area_labels"] = [POLICY_AREA_LABELS.get(a, a) for a in areas]
    rec["pregnancy_related"]  = _match(hay, _PREGNANCY_KW)
    rec["canadian"]           = (
        _match(hay, _CANADIAN_KW) or
        any(d in host for d in _CANADIAN_DOMAINS)
    )
    rec["species"] = "animal" if _match(hay, _ANIMAL_KW) else "human"
    return rec


def is_relevant(rec: dict) -> bool:
    """
    Return True only if the record is relevant to COVID-19 vaccination policy.
    Requires mention of COVID/SARS-CoV-2 AND either vaccination OR epi context.
    """
    hay   = _hay(rec)
    title = rec.get("title", "").lower()

    covid_kw = [
        "covid-19", "covid 19", "sars-cov-2", "sars cov 2",
        "coronavirus disease 2019", "coronavirus disease",
    ]
    vacc_kw = [
        "vaccin", "immuniz", "immunis", "mrna", "bnt162", "mrna-1273",
        "spikevax", "comirnaty", "booster", "primary series",
        "protection", "efficacy", "effectiveness", "immunity",
        "antibod", "seroconversion", "neutrali",
        "recommendation", "guidance", "guideline", "policy",
    ]
    epi_kw = [
        "surveillance", "outbreak", "incidence", "prevalence",
        "epidemiol", "hospitali", "icu ", "mortality", "excess death",
        "wastewater", "variant", "sequenc",
    ]

    if not _match(hay, covid_kw):
        return False
    if _match(hay, vacc_kw) or _match(hay, epi_kw):
        return True
    return False


def passes_inclusion(rec: dict) -> bool:
    """Basic quality gate — reject very short titles, retractions, etc."""
    title = (rec.get("title") or "").strip()
    if not title or len(title) < 10:
        return False
    lower = title.lower()
    if any(x in lower for x in ["corrigendum", "erratum", "retraction", "retracted", "withdrawn"]):
        return False
    return True
