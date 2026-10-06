"""
COVID-19 Evidence Watch — shared configuration constants.
"""

# Altmetric free API endpoint (no key required for basic score)
ALTMETRIC_API = "https://api.altmetric.com/v1/pmid/{pmid}"

# Europe PMC REST API
EUROPMC_API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

# ClinicalTrials.gov v2 API
CLINICALTRIALS_API = "https://clinicaltrials.gov/api/v2/studies"

# Known pharma/manufacturer domains (flagged but not excluded)
PHARMA_HOSTS = {
    "pfizer.com", "modernatx.com", "moderna.com",
    "janssen.com", "astrazeneca.com", "novavax.com",
    "sanofi.com", "gsk.com", "merck.com",
    "biontech.com", "biontech.de",
}

# Request timeout (seconds)
TIMEOUT = 20

# Max records per fetcher (to keep evidence.json manageable)
MAX_PER_FETCHER = 200
