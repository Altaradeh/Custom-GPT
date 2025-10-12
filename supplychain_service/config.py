from pathlib import Path


# ──────────────────────────── Supply Chain Data Files ────────────────────────────────
SUPPLY_CHAIN_DATA_DIR = Path("data") / "supply_chain_data"
COMPANY_MAIN_PRODUCTS_FILE = SUPPLY_CHAIN_DATA_DIR / "company_main_products.csv"
TIER_1_INPUT_PRODUCTS_FILE = SUPPLY_CHAIN_DATA_DIR / "tier_1_input_products_data.csv"
TIER_2_INPUT_PRODUCTS_FILE = SUPPLY_CHAIN_DATA_DIR / "tier_2_input_products_data.csv"
TIER_1_LOCATIONS_FILE = SUPPLY_CHAIN_DATA_DIR / "tier_1_locations_data.csv"
TIER_2_LOCATIONS_FILE = SUPPLY_CHAIN_DATA_DIR / "tier_2_locations_data.csv"
