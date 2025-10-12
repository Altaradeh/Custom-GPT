"""Generate precomputed supply chain analytical CSVs from existing raw data.

Outputs (saved into data/precomputed/):
  - supply_chain_paths.csv
  - product_aliases.csv
  - industry_exposure.csv
  - company_product_exposure.csv
  - event_summary.csv
  - location_summary.csv
  - product_similarity.csv
  - scenario_expansions.csv
  - indirect_exposures.csv
  - scenario_overlap_summary.csv

Safe assumptions:
  * Raw CSV encodings are UTF-8.
  * share_pct and Percentage Cost columns are numeric or coercible.
  * Large tables can be processed in-memory (adjust if memory constrained).

Run:
  python generate_precomputed.py
"""
from __future__ import annotations
import os
import math
import json
import itertools
from pathlib import Path
from typing import List, Dict, Tuple

import pandas as pd
import networkx as nx
from rapidfuzz import fuzz

# ---------------- Configuration ----------------
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
SC_DIR = DATA_DIR / "supply_chain_data"
OUT_DIR = DATA_DIR / "precomputed"
COMPACT_DIR = OUT_DIR / "compact"
OUT_DIR.mkdir(parents=True, exist_ok=True)
COMPACT_DIR.mkdir(parents=True, exist_ok=True)

# Raw file paths (do not rename originals; keep central reference)
KB_FILE = DATA_DIR / "knowledge_base.csv"
EVENT_TO_COMMODITY_FILE = DATA_DIR / "event_to_commodity.csv"
COMPANY_MAIN_PRODUCTS_FILE = SC_DIR / "company_main_products.csv"
T1_INPUTS_FILE = SC_DIR / "tier_1_input_products_data.csv"
T2_INPUTS_FILE = SC_DIR / "tier_2_input_products_data.csv"
T1_LOC_FILE = SC_DIR / "tier_1_locations_data.csv"
T2_LOC_FILE = SC_DIR / "tier_2_locations_data.csv"

# --------------- Helpers -----------------------

def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path)


def normalize_str(s: str) -> str:
    if pd.isna(s):
        return ""
    return str(s).strip().lower()

# --------------- Load raw data -----------------
print("[INFO] Loading raw datasets ...")
kb_df = read_csv(KB_FILE)
event_df = read_csv(EVENT_TO_COMMODITY_FILE)
company_products_df = read_csv(COMPANY_MAIN_PRODUCTS_FILE)
t1_inputs_df = read_csv(T1_INPUTS_FILE)
t2_inputs_df = read_csv(T2_INPUTS_FILE)
t1_loc_df = read_csv(T1_LOC_FILE)
t2_loc_df = read_csv(T2_LOC_FILE)

# --------------- Build graph for paths ---------
# Graph edges:
# Tier 2 Input Product -> Tier 1 / Main Product Name (from t2)
# Tier 1 Input Product -> Main Product Name (from t1)
print("[INFO] Building supply chain graph ...")
G = nx.DiGraph()

# Add Tier 2 edges
for _, r in t2_inputs_df.iterrows():
    ip = normalize_str(r.get("Input Product"))
    mp = normalize_str(r.get("Main Product Name") or r.get("Main Product") or r.get("Main Product Name"))
    if not ip or not mp:
        continue
    cost = r.get("Percentage Cost")
    try:
        cost = float(cost)
    except Exception:
        cost = math.nan
    G.add_edge(ip, mp, percentage_cost=cost)

# Add Tier 1 edges
for _, r in t1_inputs_df.iterrows():
    ip = normalize_str(r.get("Input Product"))
    mp = normalize_str(r.get("Main Product Name") or r.get("Main Product") or r.get("Main Product Name"))
    if not ip or not mp:
        continue
    cost = r.get("Percentage Cost")
    try:
        cost = float(cost)
    except Exception:
        cost = math.nan
    G.add_edge(ip, mp, percentage_cost=cost)

# Attach companies to product nodes
product_company_map = {}
for _, r in company_products_df.iterrows():
    prod = normalize_str(r.get("Product Name"))
    ticker = r.get("Ticker")
    industry = r.get("Industry")
    if prod:
        d = product_company_map.setdefault(prod, {"tickers": set(), "industries": set()})
        if not pd.isna(ticker):
            d["tickers"].add(str(ticker).strip())
        if not pd.isna(industry):
            d["industries"].add(str(industry).strip())

# --------------- supply_chain_paths.csv --------
print("[INFO] Enumerating paths (depth<=3) ...")
paths_records = []
max_depth = 3
path_id_counter = 1

# Safeguards to avoid combinatorial explosion
MAX_TOTAL_PATHS = int(os.environ.get("MAX_TOTAL_PATHS", 50000))
MAX_PATHS_PER_ROOT = int(os.environ.get("MAX_PATHS_PER_ROOT", 3000))
truncated = False

# Root candidates are any input products appearing as a source
root_candidates = {u for u, v in G.out_degree() if G.out_degree(u) > 0}
leaf_nodes = [n for n, v in G.out_degree() if v == 0]

for root in root_candidates:
    if truncated:
        break
    per_root_count = 0
    for leaf in leaf_nodes:
        if truncated:
            break
        if root == leaf:
            continue
        if not nx.has_path(G, root, leaf):
            continue
        for p in nx.all_simple_paths(G, root, leaf, cutoff=max_depth):
            depth = len(p) - 1
            # Collect edge costs
            edge_costs = []
            cumulative_cost = None
            multiplicative_cost = 1.0
            complete_cost = True
            for a, b in zip(p[:-1], p[1:]):
                data = G.get_edge_data(a, b) or {}
                c = data.get("percentage_cost")
                if c is None or (isinstance(c, float) and math.isnan(c)):
                    complete_cost = False
                else:
                    edge_costs.append(c)
                    multiplicative_cost *= (c / 100.0)
            if complete_cost and edge_costs:
                cumulative_cost = multiplicative_cost * 100.0  # express as %
            node_sequence = " > ".join(p)
            companies = sorted(set(itertools.chain.from_iterable(product_company_map.get(n, {}).get("tickers", []) for n in p)))
            industries = sorted(set(itertools.chain.from_iterable(product_company_map.get(n, {}).get("industries", []) for n in p)))
            paths_records.append({
                "path_id": f"P{path_id_counter}",
                "root_product": root,
                "final_product": leaf,
                "depth": depth,
                "node_sequence": node_sequence,
                "companies": ";".join(companies),
                "industries": ";".join(industries),
                "edge_costs_percent": "|".join(str(x) for x in edge_costs) if edge_costs else "",
                "cumulative_cost": round(cumulative_cost, 4) if cumulative_cost is not None else ""
            })
            path_id_counter += 1
            per_root_count += 1
            if per_root_count >= MAX_PATHS_PER_ROOT or len(paths_records) >= MAX_TOTAL_PATHS:
                truncated = True
                break
            # Progress heartbeat every 5000 paths
            if path_id_counter % 5000 == 0:
                print(f"[PROGRESS] Enumerated {path_id_counter} paths so far (current root={root})")

paths_df = pd.DataFrame(paths_records)
if truncated:
    print(f"[WARN] Path enumeration truncated (total_paths={len(paths_df)}) due to limits: MAX_TOTAL_PATHS={MAX_TOTAL_PATHS} or MAX_PATHS_PER_ROOT={MAX_PATHS_PER_ROOT}")
# Skip full version - generate compact only
print(f"[INFO] Generated {len(paths_df)} paths (skipping full save, proceeding to compact)")

# --------------- product_aliases.csv -----------
print("[INFO] Building product aliases from knowledge base terms + synonyms ...")
aliases_records = []
for _, r in kb_df.iterrows():
    canonical = str(r.get("Term", "")).strip()
    type_ = r.get("Type", "")
    syn_raw = r.get("Synonyms", "")
    syn_list = []
    if isinstance(syn_raw, str) and syn_raw.strip():
        # split by comma
        syn_list = [s.strip() for s in syn_raw.split(",") if s.strip()]
    all_aliases = {canonical} | set(syn_list)
    for a in all_aliases:
        # simple heuristic confidence: canonical highest, synonyms medium
        conf = 0.95 if a == canonical else 0.75
        aliases_records.append({
            "canonical_term": canonical,
            "alias": a,
            "match_confidence": conf,
            "type": type_
        })
product_aliases_df = pd.DataFrame(aliases_records)
# Skip full version
print(f"[INFO] Generated {len(product_aliases_df)} aliases (skipping full save)")

# --------------- industry_exposure.csv ---------
print("[INFO] Computing industry exposure ...")
# Map products to industries via company-main-products table
a_industry = company_products_df[['Product Name', 'Industry']].dropna().copy()
a_industry['Product Name_norm'] = a_industry['Product Name'].str.lower()

industry_counts = (
    a_industry.groupby(['Product Name_norm', 'Industry'])
    .size()
    .reset_index(name='company_product_pairs')
)
# chain_count approximated by number of paths where product appears
if not paths_df.empty:
    product_in_paths = paths_df['node_sequence'].str.split(' > ').explode()
    chain_counts = (product_in_paths.value_counts()
                    .reset_index()
                    .set_axis(['product','chain_count'], axis=1))
else:
    chain_counts = pd.DataFrame(columns=['product', 'chain_count'])

industry_exposure_rows = []
for _, row in industry_counts.iterrows():
    prod = row['Product Name_norm']
    industry = row['Industry']
    company_pairs = row['company_product_pairs']
    cc_series = chain_counts.loc[chain_counts['product'] == prod, 'chain_count']
    chain_count = int(cc_series.iloc[0]) if not cc_series.empty else 0
    exposure_score = company_pairs + chain_count  # naive additive
    industry_exposure_rows.append({
        "product": prod,
        "industry": industry,
        "chain_count": chain_count,
        "company_count": company_pairs,
        "exposure_score": exposure_score
    })
industry_exposure_df = pd.DataFrame(industry_exposure_rows)
# Skip full version
print(f"[INFO] Generated {len(industry_exposure_df)} industry exposures (skipping full save)")

# --------------- company_product_exposure.csv --
print("[INFO] Computing company product exposure ...")
cp = company_products_df[['Ticker', 'Product Name', 'share_pct']].copy()
cp['share_pct'] = pd.to_numeric(cp['share_pct'], errors='coerce')
# bucket
def bucket(x):
    if pd.isna(x):
        return "unknown"
    if x >= 50:
        return "High"
    if x >= 20:
        return "Medium"
    if x > 0:
        return "Low"
    return "None"
cp['exposure_bucket'] = cp['share_pct'].map(bucket)
cp['exposure_index'] = cp['share_pct'].fillna(0) / 100.0
company_product_exposure_df = cp.rename(columns={'Product Name': 'product', 'Ticker': 'ticker'})[
    ['ticker', 'product', 'exposure_bucket', 'exposure_index']
]
# Skip full version
print(f"[INFO] Generated {len(company_product_exposure_df)} company exposures (skipping full save)")

# --------------- event_summary.csv -------------
print("[INFO] Computing event summary ...")
if not event_df.empty:
    event_summary_rows = []
    for ev, sub in event_df.groupby('Event'):
        commodities = sorted(set(sub['Commodity'].dropna().astype(str)))
        event_summary_rows.append({
            "event": ev,
            "linked_commodities": ";".join(commodities),
            "representative_products": ";".join(commodities[:5]),
            "top_companies": "",  # placeholder; could map commodities to companies if resolvable
        })
    event_summary_df = pd.DataFrame(event_summary_rows)
else:
    event_summary_df = pd.DataFrame(columns=["event","linked_commodities","representative_products","top_companies"])

# Skip full version
print(f"[INFO] Generated {len(event_summary_df)} event summaries (skipping full save)")

# --------------- location_summary.csv ----------
print("[INFO] Computing location summary ...")
loc_rows = []
if not t1_loc_df.empty:
    for loc, sub in t1_loc_df.groupby('Location'):
        products = sorted(set(sub['Product Name'].dropna().astype(str)))
        companies = sorted(set(sub['Company Name'].dropna().astype(str)))
        industries = []  # not directly present here; could be enriched
        loc_rows.append({
            "location": loc,
            "products": ";".join(products),
            "industries": ";".join(industries),
            "distinct_product_count": len(products),
            "distinct_industry_count": len(industries)
        })
location_summary_df = pd.DataFrame(loc_rows)
# Skip full version
print(f"[INFO] Generated {len(location_summary_df)} location summaries (skipping full save)")

# --------------- product_similarity.csv --------
print("[INFO] Computing basic product similarity (token fuzz over product names) ...")
products_list = sorted(set(company_products_df['Product Name'].dropna().astype(str)))
# Limit comparisons for performance if extremely large
max_pairs = 30000
sim_rows = []
for i, a in enumerate(products_list):
    for b in products_list[i+1:]:
        score = fuzz.token_set_ratio(a, b) / 100.0
        if score < 0.5:
            continue
        sim_rows.append({"product_a": a, "product_b": b, "similarity_score": round(score, 4)})
        if len(sim_rows) >= max_pairs:
            break
    if len(sim_rows) >= max_pairs:
        break
product_similarity_df = pd.DataFrame(sim_rows)
# rank per product_a
product_similarity_df['rank'] = product_similarity_df.groupby('product_a')['similarity_score'].rank(method='first', ascending=False)
# Skip full version
print(f"[INFO] Generated {len(product_similarity_df)} similarities (skipping full save)")

# --------------- scenario_expansions.csv -------
print("[INFO] Computing scenario expansions (events + direct commodities) ...")
scenario_rows = []
for _, r in event_summary_df.iterrows():
    scenario_rows.append({
        "scenario": r['event'],
        "type": "event",
        "linked_commodities": r['linked_commodities'],
        "linked_products": r['representative_products'],
        "top_companies": r['top_companies'],
        "industries": ""
    })
# Locations as scenarios (basic: gather associated products)
if not t1_loc_df.empty:
    for loc, sub in t1_loc_df.groupby('Location'):
        products = sorted(set(sub['Product Name'].dropna().astype(str)))
        scenario_rows.append({
            "scenario": loc,
            "type": "location",
            "linked_commodities": "",
            "linked_products": ";".join(products[:10]),
            "top_companies": ";".join(sorted(set(sub['Company Name'].dropna().astype(str)))[:10]),
            "industries": ""
        })
scenario_expansions_df = pd.DataFrame(scenario_rows)
# Skip full version
print(f"[INFO] Generated {len(scenario_expansions_df)} scenario expansions (skipping full save)")

# --------------- indirect_exposures.csv --------
print("[INFO] Skipping indirect exposures computation and output as per new requirements.")
# The following block is intentionally disabled:
# indirect_rows = []
# for root in root_candidates:
#     # BFS up to depth 3
#     if root not in G:
#         continue
#     for target in G.nodes:
#         if target == root:
#             continue
#         if not nx.has_path(G, root, target):
#             continue
#         # get shortest path length
#         try:
#             length = nx.shortest_path_length(G, root, target)
#         except Exception:
#             continue
#         if length >= 2:  # indirect
#             indirect_rows.append({
#                 "root_product": root,
#                 "indirect_product": target,
#                 "minimal_path_length": length,
#                 "count_of_paths": sum(1 for _ in nx.all_simple_paths(G, root, target, cutoff=length))
#             })

# --------------- scenario_overlap_summary.csv --
print("[INFO] Computing scenario overlap summary (company occurrences per scenario) ...")
overlap_rows = []
# Use scenario_expansions linked products -> map to companies via company_products_df
prod_to_companies = company_products_df.groupby('Product Name')['Ticker'].apply(lambda s: sorted(set(s.dropna().astype(str)))).to_dict()
for _, r in scenario_expansions_df.iterrows():
    scen = r['scenario']
    linked_products = [p.strip() for p in str(r['linked_products']).split(';') if p.strip()]
    company_counter = {}
    for p in linked_products:
        comps = prod_to_companies.get(p, [])
        for c in comps:
            company_counter[c] = company_counter.get(c, 0) + 1
    for comp, occ in company_counter.items():
        overlap_rows.append({
            "scenario": scen,
            "company": comp,
            "occurrence_count": occ,
            "distinct_products": len(linked_products),
            "overlap_rank": None  # fill later
        })
scenario_overlap_df = pd.DataFrame(overlap_rows)
if not scenario_overlap_df.empty:
    scenario_overlap_df['overlap_rank'] = scenario_overlap_df.groupby('scenario')['occurrence_count'].rank(method='first', ascending=False)
# Skip full version
print(f"[INFO] Generated {len(scenario_overlap_df)} scenario overlaps (skipping full save)")

print("[INFO] Skipped full versions - proceeding directly to compact generation...")

# ============================================================================
# COMPACT VERSION GENERATION (for Custom GPT 128k-200k token limit)
# ============================================================================

print("\n[INFO] Generating compact versions for Custom GPT upload...")

# Create string-to-ID mappings for commonly repeated strings
product_to_id = {}
company_to_id = {}
industry_to_id = {}
location_to_id = {}
event_to_id = {}

id_counter = 1

def get_or_create_id(item: str, mapping: dict) -> int:
    global id_counter
    if not item or pd.isna(item):
        return 0  # Reserve 0 for empty/null
    item = str(item).strip()
    if item not in mapping:
        mapping[item] = id_counter
        id_counter += 1
    return mapping[item]

# Build ID mappings from all data sources
print("[COMPACT] Building string-to-ID mappings...")

# Products from all sources
all_products = set()
all_products.update(company_products_df['Product Name'].dropna().astype(str))
all_products.update(t1_inputs_df['Input Product'].dropna().astype(str))
all_products.update(t1_inputs_df['Main Product Name'].dropna().astype(str))
all_products.update(t2_inputs_df['Input Product'].dropna().astype(str))
all_products.update(t2_inputs_df['Main Product Name'].dropna().astype(str))

for prod in sorted(all_products):
    get_or_create_id(prod, product_to_id)

# Companies
for company in sorted(set(company_products_df['Ticker'].dropna().astype(str))):
    get_or_create_id(company, company_to_id)

# Industries
for industry in sorted(set(company_products_df['Industry'].dropna().astype(str))):
    get_or_create_id(industry, industry_to_id)

# Locations
if not t1_loc_df.empty:
    for location in sorted(set(t1_loc_df['Location'].dropna().astype(str))):
        get_or_create_id(location, location_to_id)

# Events
if not event_df.empty:
    for event in sorted(set(event_df['Event'].dropna().astype(str))):
        get_or_create_id(event, event_to_id)

# Save lookup tables
lookups = {
    "products": {v: k for k, v in product_to_id.items()},
    "companies": {v: k for k, v in company_to_id.items()},
    "industries": {v: k for k, v in industry_to_id.items()},
    "locations": {v: k for k, v in location_to_id.items()},
    "events": {v: k for k, v in event_to_id.items()}
}

lookup_out = COMPACT_DIR / "string_lookups.json"
with open(lookup_out, 'w') as f:
    json.dump(lookups, f, indent=2)
print(f"[COMPACT] Wrote {lookup_out}")

# ================ COMPACT PATHS ================
print("[COMPACT] Creating compact supply chain paths...")
# Keep only top 30 paths per root, prioritize by depth then cumulative cost
MAX_PATHS_PER_ROOT_COMPACT = 30

if not paths_df.empty:
    # Add sorting keys
    paths_compact = paths_df.copy()
    paths_compact['sort_cost'] = pd.to_numeric(paths_compact['cumulative_cost'], errors='coerce').fillna(999999)
    
    # Group by root and take top N
    compact_paths_list = []
    for root, group in paths_compact.groupby('root_product'):
        top_paths = (group.sort_values(['depth', 'sort_cost', 'node_sequence'])
                    .head(MAX_PATHS_PER_ROOT_COMPACT))
        compact_paths_list.append(top_paths)
    
    paths_compact_df = pd.concat(compact_paths_list, ignore_index=True)
    
    # Convert to IDs and create separate manifest
    paths_minimal = paths_compact_df[['path_id', 'root_product', 'final_product', 'depth', 'cumulative_cost']].copy()
    paths_minimal['root_id'] = paths_minimal['root_product'].apply(lambda x: product_to_id.get(x, 0))
    paths_minimal['final_id'] = paths_minimal['final_product'].apply(lambda x: product_to_id.get(x, 0))
    paths_minimal = paths_minimal[['path_id', 'root_id', 'final_id', 'depth', 'cumulative_cost']]
    
    # Separate chain manifest (for full sequences)
    chains_manifest = paths_compact_df[['path_id', 'node_sequence']].copy()
    
    paths_minimal_out = COMPACT_DIR / "paths_compact.csv"
    chains_manifest_out = COMPACT_DIR / "chains_manifest.csv"
    
    paths_minimal.to_csv(paths_minimal_out, index=False)
    chains_manifest.to_csv(chains_manifest_out, index=False)
    
    print(f"[COMPACT] Wrote {paths_minimal_out} ({len(paths_minimal)} rows)")
    print(f"[COMPACT] Wrote {chains_manifest_out} ({len(chains_manifest)} rows)")

# ================ MERGED SCENARIO SUMMARY ================
print("[COMPACT] Creating merged scenario summary...")

scenario_merged_rows = []

# Add events
if not event_summary_df.empty:
    for _, r in event_summary_df.iterrows():
        commodities = str(r['linked_commodities']).split(';')[:8]  # limit to 8
        scenario_merged_rows.append({
            "scenario_id": event_to_id.get(r['event'], 0),
            "scenario_type": "event",
            "linked_items": ";".join(commodities),
            "item_count": len([c for c in commodities if c.strip()])
        })

# Add locations
if not location_summary_df.empty:
    for _, r in location_summary_df.iterrows():
        products = str(r['products']).split(';')[:8]  # limit to 8
        scenario_merged_rows.append({
            "scenario_id": location_to_id.get(r['location'], 0),
            "scenario_type": "location", 
            "linked_items": ";".join(products),
            "item_count": len([p for p in products if p.strip()])
        })

scenario_merged_df = pd.DataFrame(scenario_merged_rows)
scenario_merged_out = COMPACT_DIR / "scenario_summary.csv"
scenario_merged_df.to_csv(scenario_merged_out, index=False)
print(f"[COMPACT] Wrote {scenario_merged_out} ({len(scenario_merged_df)} rows)")

# ================ COMPACT INDUSTRY EXPOSURE ================
print("[COMPACT] Creating top industry exposures...")

if not industry_exposure_df.empty:
    # Keep only top 3 industries per product
    industry_compact_list = []
    for prod, group in industry_exposure_df.groupby('product'):
        top_industries = group.nlargest(3, 'exposure_score')
        industry_compact_list.append(top_industries)
    
    industry_compact_df = pd.concat(industry_compact_list, ignore_index=True)
    
    # Convert to IDs
    industry_compact_df['product_id'] = industry_compact_df['product'].apply(lambda x: product_to_id.get(x, 0))
    industry_compact_df['industry_id'] = industry_compact_df['industry'].apply(lambda x: industry_to_id.get(x, 0))
    industry_compact_df['rank'] = industry_compact_df.groupby('product_id')['exposure_score'].rank(method='first', ascending=False)
    
    industry_compact_final = industry_compact_df[['product_id', 'industry_id', 'exposure_score', 'rank']].copy()
    industry_compact_out = COMPACT_DIR / "industry_exposure_top.csv"
    industry_compact_final.to_csv(industry_compact_out, index=False)
    print(f"[COMPACT] Wrote {industry_compact_out} ({len(industry_compact_final)} rows)")

# ================ COMPACT COMPANY EXPOSURE ================
print("[COMPACT] Creating compact company exposure...")

if not company_product_exposure_df.empty:
    # Filter out 'None' and 'unknown' exposures, convert to IDs
    company_compact = company_product_exposure_df[
        ~company_product_exposure_df['exposure_bucket'].isin(['None', 'unknown'])
    ].copy()
    
    company_compact['ticker_id'] = company_compact['ticker'].apply(lambda x: company_to_id.get(x, 0))
    company_compact['product_id'] = company_compact['product'].apply(lambda x: product_to_id.get(x, 0))
    
    company_compact_final = company_compact[['ticker_id', 'product_id', 'exposure_bucket']].copy()
    company_compact_out = COMPACT_DIR / "company_exposure_compact.csv"
    company_compact_final.to_csv(company_compact_out, index=False)
    print(f"[COMPACT] Wrote {company_compact_out} ({len(company_compact_final)} rows)")

# ================ COMPACT SIMILARITY (TOP 3 PER PRODUCT) ================
print("[COMPACT] Creating top product similarities...")

if not product_similarity_df.empty:
    # Keep only top 3 similarities per product, high threshold
    sim_filtered = product_similarity_df[product_similarity_df['similarity_score'] >= 0.65].copy()
    
    similarity_compact_list = []
    for prod, group in sim_filtered.groupby('product_a'):
        top_sims = group.nlargest(3, 'similarity_score')
        similarity_compact_list.append(top_sims)
    
    if similarity_compact_list:
        similarity_compact_df = pd.concat(similarity_compact_list, ignore_index=True)
        
        # Convert to IDs
        similarity_compact_df['product_a_id'] = similarity_compact_df['product_a'].apply(lambda x: product_to_id.get(x, 0))
        similarity_compact_df['product_b_id'] = similarity_compact_df['product_b'].apply(lambda x: product_to_id.get(x, 0))
        
        similarity_compact_final = similarity_compact_df[['product_a_id', 'product_b_id', 'similarity_score']].copy()
        similarity_compact_out = COMPACT_DIR / "similarity_top.csv"
        similarity_compact_final.to_csv(similarity_compact_out, index=False)
        print(f"[COMPACT] Wrote {similarity_compact_out} ({len(similarity_compact_final)} rows)")

print("[COMPACT] Skipping indirect exposure summary as per new requirements.")

# ================ OVERLAP TOP (TOP 5 PER SCENARIO) ================
print("[COMPACT] Creating top scenario overlaps...")

if not scenario_overlap_df.empty:
    overlap_compact_list = []
    for scenario, group in scenario_overlap_df.groupby('scenario'):
        top_overlaps = group.nsmallest(5, 'overlap_rank')  # rank 1-5
        overlap_compact_list.append(top_overlaps)
    
    overlap_compact_df = pd.concat(overlap_compact_list, ignore_index=True)
    
    # Convert to IDs  
    overlap_compact_df['scenario_id'] = overlap_compact_df['scenario'].apply(
        lambda x: event_to_id.get(x, location_to_id.get(x, 0))
    )
    overlap_compact_df['company_id'] = overlap_compact_df['company'].apply(lambda x: company_to_id.get(x, 0))
    
    overlap_compact_final = overlap_compact_df[['scenario_id', 'company_id', 'occurrence_count', 'overlap_rank']].copy()
    overlap_compact_out = COMPACT_DIR / "overlap_top.csv"
    overlap_compact_final.to_csv(overlap_compact_out, index=False)
    print(f"[COMPACT] Wrote {overlap_compact_out} ({len(overlap_compact_final)} rows)")

# ================ SIMPLE PRODUCT ALIASES (no IDs needed) ================
if not product_aliases_df.empty:
    aliases_compact_out = COMPACT_DIR / "product_aliases.csv"
    product_aliases_df.to_csv(aliases_compact_out, index=False)
    print(f"[COMPACT] Copied {aliases_compact_out} ({len(product_aliases_df)} rows)")

# ================ MANIFEST ================
manifest = {
    "version": "1.0",  
    "generated_at": "2025-10-12",
    "limits": {
        "max_paths_per_root": MAX_PATHS_PER_ROOT_COMPACT,
        "max_depth": max_depth,
        "max_industries_per_product": 3,
        "max_similarities_per_product": 3,
        "max_indirect_targets_listed": 5,
        "max_overlaps_per_scenario": 5,
        "similarity_threshold": 0.65
    },
    "files": {
        "string_lookups.json": {"purpose": "ID-to-string mappings", "categories": 5},
        "paths_compact.csv": {"rows": len(paths_minimal) if 'paths_minimal' in locals() else 0, "note": "Top paths per root with IDs"},
        "chains_manifest.csv": {"rows": len(chains_manifest) if 'chains_manifest' in locals() else 0, "note": "Full node sequences"},
        "scenario_summary.csv": {"rows": len(scenario_merged_df), "note": "Events + locations merged"},
        "industry_exposure_top.csv": {"rows": len(industry_compact_final) if 'industry_compact_final' in locals() else 0, "note": "Top 3 per product"},
        "company_exposure_compact.csv": {"rows": len(company_compact_final) if 'company_compact_final' in locals() else 0, "note": "Non-zero exposures only"},
        "similarity_top.csv": {"rows": len(similarity_compact_final) if 'similarity_compact_final' in locals() else 0, "note": "Top 3 per product"},
    # "indirect_summary.csv": {"rows": 0, "note": "Aggregated counts (skipped)"},
        "overlap_top.csv": {"rows": len(overlap_compact_final) if 'overlap_compact_final' in locals() else 0, "note": "Top 5 per scenario"},
        "product_aliases.csv": {"rows": len(product_aliases_df), "note": "Unchanged from full version"}
    }
}

manifest_out = COMPACT_DIR / "manifest.json"
with open(manifest_out, 'w') as f:
    json.dump(manifest, f, indent=2)
print(f"[COMPACT] Wrote {manifest_out}")

# Calculate total size
total_size = sum(f.stat().st_size for f in COMPACT_DIR.iterdir() if f.is_file())
total_size_kb = total_size / 1024
approx_tokens = total_size / 4  # rough estimate

print(f"\n[COMPACT] Total compact size: {total_size_kb:.1f} KB (~{approx_tokens:.0f} tokens)")
if approx_tokens > 150000:
    print("[WARN] Size may exceed Custom GPT limits - consider further reduction")

print(f"[DONE] Compact files ready for Custom GPT in: {COMPACT_DIR}")
