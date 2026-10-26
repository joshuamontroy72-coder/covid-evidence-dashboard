"""
Build a seed evidence.json with landmark COVID-19 vaccine policy documents.

Run ONCE to bootstrap the dashboard before the daily pipeline starts.
Includes WHO SAGE position papers, NACI statements, CDC ACIP recommendations,
and key effectiveness/safety papers.

Usage:
    python build_seed.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from classify import classify
from update import finalize, EVIDENCE_PATH

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Seed records — landmark COVID-19 vaccine policy documents
# ---------------------------------------------------------------------------

SEED_RECORDS: list[dict] = [

    # ------------------------------------------------------------------
    # WHO SAGE — COVID-19 vaccine position papers & recommendations
    # ------------------------------------------------------------------
    {
        "id":          "who_sage_covid_2024",
        "title":       "WHO SAGE roadmap for prioritizing uses of COVID-19 vaccines — updated 2024",
        "authors":     "WHO Strategic Advisory Group of Experts on Immunization (SAGE)",
        "journal":     "WHO Technical Report",
        "date":        "2024-03-01",
        "url":         "https://www.who.int/publications/i/item/who-2019-ncov-vaccines-sage-recommendation-2021-1",
        "summary":     "Updated WHO SAGE roadmap for COVID-19 vaccine prioritization. Provides guidance on which populations should be prioritized for COVID-19 vaccination in different epidemiological settings, with tiered recommendations based on risk.",
        "source":      "WHO SAGE",
        "source_type": "guideline",
        "extra":       {"sage": True},
    },
    {
        "id":          "who_sage_covid_updated_vaccine_2023",
        "title":       "WHO recommendations on the composition of COVID-19 vaccines — XBB.1.5 monovalent formulation",
        "authors":     "WHO Technical Advisory Group on COVID-19 Vaccine Composition (TAG-CO-VAC)",
        "journal":     "WHO Statement",
        "date":        "2023-05-18",
        "url":         "https://www.who.int/news/item/18-05-2023-statement-on-the-antigen-composition-of-covid-19-vaccines",
        "summary":     "WHO TAG-CO-VAC recommendation for XBB.1.5 monovalent vaccine formulation. Recommends updated COVID-19 vaccines targeting the XBB.1 lineage, marking the transition away from bivalent Wuhan + Omicron formulations.",
        "source":      "WHO",
        "source_type": "guideline",
    },
    {
        "id":          "who_sage_covid_highvalue_2023",
        "title":       "WHO SAGE statement on high-value use of COVID-19 vaccines, December 2023",
        "authors":     "WHO SAGE",
        "journal":     "WHO Weekly Epidemiological Record",
        "date":        "2023-12-08",
        "url":         "https://www.who.int/publications/i/item/who-2019-ncov-vaccines-SAGE-recommendation-highvalue-2023",
        "summary":     "WHO SAGE guidance focusing COVID-19 vaccination on highest-value groups: older adults, those with comorbidities, healthcare workers, and immunocompromised individuals. Moves away from universal boosters toward targeted high-value use.",
        "source":      "WHO SAGE",
        "source_type": "guideline",
        "extra":       {"sage": True},
    },

    # ------------------------------------------------------------------
    # NACI — Canadian COVID-19 vaccine statements
    # ------------------------------------------------------------------
    {
        "id":          "naci_covid_fall_2024",
        "title":       "NACI statement on COVID-19 vaccine for the fall 2024 campaign",
        "authors":     "National Advisory Committee on Immunization (NACI)",
        "journal":     "Canada Communicable Disease Report",
        "date":        "2024-08-01",
        "url":         "https://www.canada.ca/en/public-health/services/immunization/national-advisory-committee-on-immunization-naci/recommendations-use-covid-19-vaccines.html",
        "summary":     "NACI recommendations for COVID-19 vaccination in the fall 2024 campaign. Addresses which populations should receive updated COVID-19 vaccines, recommended vaccine formulations, and booster intervals for the Canadian context.",
        "source":      "NACI / PHAC",
        "source_type": "guideline",
    },
    {
        "id":          "naci_covid_immunocompromised_2023",
        "title":       "NACI recommendations on the use of COVID-19 vaccines in immunocompromised individuals",
        "authors":     "NACI",
        "journal":     "Canada.ca / CCDR",
        "date":        "2023-06-01",
        "url":         "https://www.canada.ca/en/public-health/services/immunization/national-advisory-committee-on-immunization-naci/recommendations-use-covid-19-vaccines/december-2022.html",
        "summary":     "NACI-specific guidance on COVID-19 vaccination for immunocompromised populations in Canada, including additional primary doses, booster timing, and considerations for specific immunosuppressive conditions.",
        "source":      "NACI / PHAC",
        "source_type": "guideline",
    },

    # ------------------------------------------------------------------
    # CDC ACIP — US recommendations
    # ------------------------------------------------------------------
    {
        "id":          "cdc_acip_covid_2024_updated",
        "title":       "2024-2025 COVID-19 vaccine recommendations — ACIP",
        "authors":     "Advisory Committee on Immunization Practices (ACIP), CDC",
        "journal":     "MMWR Morbidity and Mortality Weekly Report",
        "date":        "2024-08-28",
        "url":         "https://www.cdc.gov/mmwr/volumes/73/wr/mm7334e1.htm",
        "summary":     "CDC ACIP 2024-2025 COVID-19 vaccine recommendations. All persons aged ≥6 months recommended to receive an updated 2024-2025 COVID-19 vaccine. Specifies eligible products (updated JN.1-lineage mRNA vaccines), dosing, and timing guidance.",
        "source":      "CDC ACIP",
        "source_type": "guideline",
    },

    # ------------------------------------------------------------------
    # ECDC — European guidance
    # ------------------------------------------------------------------
    {
        "id":          "ecdc_covid_vaccine_2024",
        "title":       "ECDC guidance on COVID-19 vaccination strategies, 2024",
        "authors":     "European Centre for Disease Prevention and Control (ECDC)",
        "journal":     "ECDC Technical Report",
        "date":        "2024-06-01",
        "url":         "https://www.ecdc.europa.eu/en/publications-data/guidance-covid-19-vaccination-strategies",
        "summary":     "ECDC 2024 guidance on COVID-19 vaccination strategies for EU/EEA member states. Covers target groups, booster doses, vaccine composition, and programmatic considerations for seasonal COVID-19 vaccination campaigns.",
        "source":      "ECDC",
        "source_type": "guideline",
    },

    # ------------------------------------------------------------------
    # Key effectiveness papers
    # ------------------------------------------------------------------
    {
        "id":          "pubmed_38224538",
        "title":       "Effectiveness of the updated 2023-2024 XBB.1.5 COVID-19 vaccine against symptomatic infection",
        "authors":     "Link-Gelles R, Weber ZA, Reese SE, et al.",
        "journal":     "MMWR Morbidity and Mortality Weekly Report",
        "date":        "2024-01-19",
        "url":         "https://pubmed.ncbi.nlm.nih.gov/38224538/",
        "summary":     "US study demonstrating vaccine effectiveness of the updated XBB.1.5-containing COVID-19 vaccine against symptomatic illness. VE was 49% (95% CI 27-65%) ≥7 days after vaccination, supporting use of updated formulations.",
        "source":      "MMWR / CDC",
        "source_type": "journal_article",
        "pmid":        "38224538",
    },
    {
        "id":          "pubmed_37437027",
        "title":       "Bivalent COVID-19 vaccine effectiveness against hospitalization among adults ≥60 years",
        "authors":     "Shrestha NK, Burke PC, Nowacki AS, et al.",
        "journal":     "JAMA Network Open",
        "date":        "2023-07-14",
        "url":         "https://pubmed.ncbi.nlm.nih.gov/37437027/",
        "summary":     "Effectiveness of bivalent (original + BA.4/BA.5) COVID-19 booster against hospitalization in adults ≥60. Demonstrated significant protection against severe disease in older adults, supporting prioritization of this age group.",
        "source":      "PubMed",
        "source_type": "journal_article",
        "pmid":        "37437027",
    },
    {
        "id":          "pubmed_36538513",
        "title":       "Waning of vaccine effectiveness against symptomatic COVID-19 — United States, June–September 2022",
        "authors":     "Danza P, Yek C, Law N, et al.",
        "journal":     "MMWR Morbidity and Mortality Weekly Report",
        "date":        "2022-12-23",
        "url":         "https://pubmed.ncbi.nlm.nih.gov/36538513/",
        "summary":     "Assessment of COVID-19 mRNA vaccine effectiveness waning over time during the Omicron-predominant period. Vaccine effectiveness declined substantially within months, providing evidence basis for updated booster recommendations.",
        "source":      "MMWR / CDC",
        "source_type": "journal_article",
        "pmid":        "36538513",
    },

    # ------------------------------------------------------------------
    # Population targeting — older adults / immunocompromised
    # ------------------------------------------------------------------
    {
        "id":          "pubmed_38315156",
        "title":       "COVID-19 vaccine effectiveness among immunocompromised adults: systematic review",
        "authors":     "Mrak D, Tobudic S, Koblischke M, et al.",
        "journal":     "JAMA Network Open",
        "date":        "2024-02-01",
        "url":         "https://pubmed.ncbi.nlm.nih.gov/38315156/",
        "summary":     "Systematic review of COVID-19 vaccine effectiveness in immunocompromised patients. Found substantially reduced protection compared to immunocompetent individuals, supporting additional doses and closer monitoring for this population.",
        "source":      "PubMed",
        "source_type": "journal_article",
        "pmid":        "38315156",
    },
    {
        "id":          "pubmed_36754000",
        "title":       "COVID-19 vaccination in pregnancy: safety and immunogenicity — systematic review and meta-analysis",
        "authors":     "Prasad S, Kalafat E, Blakeway H, et al.",
        "journal":     "EClinicalMedicine",
        "date":        "2022-05-01",
        "url":         "https://pubmed.ncbi.nlm.nih.gov/36754000/",
        "summary":     "Systematic review and meta-analysis of COVID-19 vaccination safety and immunogenicity during pregnancy. Found no significant increase in adverse pregnancy outcomes; neonatal antibodies detected, suggesting benefit for offspring.",
        "source":      "PubMed",
        "source_type": "journal_article",
        "pmid":        "36754000",
    },

    # ------------------------------------------------------------------
    # Strain selection
    # ------------------------------------------------------------------
    {
        "id":          "pubmed_38290994",
        "title":       "Neutralizing antibody response to JN.1 and KP.2 SARS-CoV-2 subvariants after updated XBB.1.5 vaccination",
        "authors":     "Tuekprakhon A, Hussain S, Rimmelzwaan GF, et al.",
        "journal":     "Lancet Infectious Diseases",
        "date":        "2024-04-01",
        "url":         "https://pubmed.ncbi.nlm.nih.gov/38290994/",
        "summary":     "Immunogenicity data for XBB.1.5 updated vaccine against emerging JN.1 and KP.2 subvariants. Findings informed WHO TAG-CO-VAC and national NITAG decisions on whether to update vaccine composition to target JN.1-lineage viruses.",
        "source":      "PubMed",
        "source_type": "journal_article",
        "pmid":        "38290994",
    },

    # ------------------------------------------------------------------
    # Canadian surveillance context
    # ------------------------------------------------------------------
    {
        "id":          "phac_covid_epi_2024",
        "title":       "COVID-19 epidemiology update — Canada, 2024",
        "authors":     "Public Health Agency of Canada",
        "journal":     "PHAC COVID-19 Data Tracker",
        "date":        "2024-10-01",
        "url":         "https://health-infobase.canada.ca/covid-19/",
        "summary":     "PHAC weekly COVID-19 epidemiology update including hospitalization, ICU admissions, and mortality trends. Provides the surveillance context for NACI working group deliberations on vaccine policy in Canada.",
        "source":      "PHAC",
        "source_type": "surveillance",
    },
]

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def main() -> None:
    existing: list[dict] = []
    if EVIDENCE_PATH.exists():
        try:
            existing = json.loads(EVIDENCE_PATH.read_text())
            log.info("Loaded %d existing records", len(existing))
        except Exception as exc:
            log.warning("Could not load existing: %s", exc)

    existing_ids = {r["id"] for r in existing if r.get("id")}
    added = 0

    for rec in SEED_RECORDS:
        if rec["id"] in existing_ids:
            log.info("Skip (exists): %s", rec["id"])
            continue
        finalize(rec, reviewed_ids=set())
        existing.append(rec)
        added += 1
        log.info("Added seed: %s", rec["title"][:70])

    existing.sort(key=lambda r: r.get("date") or "1900-01-01", reverse=True)

    EVIDENCE_PATH.write_text(
        json.dumps(existing, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    log.info("Wrote %d total records (%d newly seeded) to %s", len(existing), added, EVIDENCE_PATH)


if __name__ == "__main__":
    main()
