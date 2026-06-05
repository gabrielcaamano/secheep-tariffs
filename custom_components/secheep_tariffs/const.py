DOMAIN = "secheep_tariffs"

COORDINATOR = "coordinator"

CONF_BILLING_CYCLE_KWH = "billing_cycle_kwh"
CONF_MANUAL_BAND_INDEX = "manual_band_index"
CONF_SERVICE_AREA = "service_area"
CONF_SUBSIDY_PROFILE = "subsidy_profile"

DEFAULT_SERVICE_AREA = "Resistencia"
DEFAULT_SCAN_INTERVAL_HOURS = 24
DEFAULT_BILLING_CYCLE_KWH = 0.0
DEFAULT_MANUAL_BAND_INDEX = 0

PRICE_MODE_MANUAL_BAND = "manual_band"
PRICE_MODE_MARGINAL = "marginal"
PRICE_MODE_PROFILE_NOT_CONFIGURED = "profile_not_configured"

SUBSIDY_PROFILE_N1 = "n1_no_subsidy"
SUBSIDY_PROFILE_N2 = "n2_low_income"
SUBSIDY_PROFILE_N3 = "n3_middle_income"
SUBSIDY_PROFILE_SEF = "sef"
SUBSIDY_PROFILE_UNKNOWN = "unknown"

SOURCE_URL = "https://www.secheep.gob.ar/?page_id=5601"
FALLBACK_SOURCE_URL = (
    "https://www.argentina.gob.ar/economia/energia/energia-electrica/"
    "estadisticas/cuadros-tarifarios-secheep"
)

STORAGE_KEY = f"{DOMAIN}.tariff"
STORAGE_VERSION = 1
