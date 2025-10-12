import re, numpy as np, pandas as pd
from unidecode import unidecode
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer

COPPER_KEYWORDS = {"copper", "cu", "cupric", "cuprous"}
SUBTYPE_HINTS = {
    "ore": {"ore", "concentrate", "concentrates"},
    "oxide": {"oxide", "oxides", "hydroxide", "hydroxides"},
    "scrap": {"scrap", "waste"},
    "wire": {"wire", "winding"},
    "foil": {"foil", "backed"},
    "fastener": {"screw", "screws", "bolt", "bolts", "nut", "nuts", "washer", "washers", "rivets", "cotter", "cotter-pins"},
}

MATERIAL_HINTS = {
    # ── Energy transition & electronics ─────────────────────────────────────────
    "rare earth": {
        "chapters": ["25", "28", "85"],              # ores/mineral, chemicals, magnets/devices
        "aliases": [
            "rare earth", "rare earths", "rare-earth", "rare-earths", "ree",
            "neodymium", "praseodymium", "dysprosium", "yttrium", "scandium", "lanthanum", "cerium"
        ],
    },
    "graphite": {
        "chapters": ["25", "38"],                     # natural graphite, artificial/synthetic
        "aliases": [
            "graphite", "synthetic graphite", "artificial graphite",
            "spherical graphite", "anode-grade graphite", "battery-grade graphite", "graphite anode"
        ],
    },
    "cobalt": {
        "chapters": ["81", "26", "28"],               # metal, ores, oxides/hydroxides/sulfates
        "aliases": [
            "co", "cobalt", "cobalt oxide", "cobalt hydroxide",
            "cobalt sulfate", "cobalt sulphate", "cobalt chemicals", "refined cobalt"
        ],
    },
    "lithium": {
        "chapters": ["28", "25"],                     # Li carbonate/hydroxide (28), mineral products
        "aliases": [
            "li", "lithium", "lithium carbonate", "lithium hydroxide",
            "spodumene", "battery-grade"
        ],
    },
    "nickel": {
        "chapters": ["75", "26", "28"],               # nickel metal, ores, chemicals (e.g., sulfate)
        "aliases": [
            "ni", "nickel", "class 1 nickel", "nickel sulfate", "nickel sulphate", "nickel matte", "nickel ore"
        ],
    },
    "aluminum": {
        "chapters": ["76", "26", "28"],               # metal, bauxite (ores), alumina (oxide)
        "aliases": [
            "aluminium", "al", "aluminum", "alumina", "aluminum oxide", "aluminium oxide", "bauxite"
        ],
    },
    "copper": {
        "chapters": ["74", "26"],                     # copper, copper ores/concentrates
        "aliases": ["cu", "copper", "copper cathode", "refined copper"],
    },
    "tin": {
        "chapters": ["80", "26"],                     # tin, tin ores/concentrates
        "aliases": ["sn", "tin", "solder tin"],
    },
    "pgms": {
        "chapters": ["71", "26", "28"],               # precious metals, precious metal ores, compounds
        "aliases": [
            "pgm", "pgms", "platinum group", "platinum", "palladium",
            "rhodium", "iridium", "ruthenium", "osmium"
        ],
    },
    "titanium": {
        "chapters": ["81", "26", "28"],               # titanium metal (incl sponge), ores, TiO2
        "aliases": [
            "titanium", "titanium sponge", "tio2", "titanium dioxide", "ilmenite", "rutile"
        ],
    },
    "gallium": {
        "chapters": ["28", "81"],                     # chemicals; metal as other base metals
        "aliases": ["gallium", "ga", "gallium metal", "gallium oxide"],
    },
    "germanium": {
        "chapters": ["28", "81"],                     # chemicals; metal as other base metals
        "aliases": ["germanium", "ge", "germanium metal", "germanium dioxide"],
    },
    "fluorspar": {
        "chapters": ["25"],                           # natural calcium fluoride
        "aliases": ["fluorspar", "fluorite", "caf2", "acid-grade fluorspar"],
    },
    "phosphate": {
        "chapters": ["25", "31", "28"],               # rock, fertilizers, phosphoric acid/phosphates
        "aliases": [
            "phosphate", "phosphates", "map", "dap", "tsp", "phosphoric acid",
            "dicalcium phosphate", "monocalcium phosphate"
        ],
    },
    "tantalum": {
        "chapters": ["81", "26"],                     # metal; ores/concentrates (incl coltan)
        "aliases": ["ta", "tantalum", "coltan", "columbite-tantalite", "columbite", "tantalite"],
    },
    "manganese": {
        "chapters": ["26", "72", "81", "28"],         # ores, steel, metal, chemicals (e.g., MnO2)
        "aliases": ["mn", "manganese", "manganese ore", "manganese dioxide"],
    },
    "vanadium": {
        "chapters": ["81", "26", "28"],               # metal, ores, chemicals
        "aliases": ["v", "vanadium", "vanadium pentoxide", "v2o5"],
    },
    "chromium": {
        "chapters": ["81", "26", "28"],               # metal, ores, chemicals
        "aliases": ["cr", "chromium", "chromite", "sodium dichromate", "chromium oxide"],
    },

    # ── Semiconductor & high-tech inputs ────────────────────────────────────────
    "photolithography": {
        "chapters": ["84"],                           # lithography equipment
        "aliases": ["euv", "duv", "lithography", "asml", "photolithography"],
    },
    "silicon wafers": {
        "chapters": ["38", "28"],                     # 3818 wafers; 2804 polysilicon feedstock
        "aliases": [
            "silicon wafer", "prime wafer", "epitaxial wafer", "epi wafer",
            "300mm wafer", "200mm wafer", "soi wafer", "polysilicon"
        ],
    },
    "fluorinated gases": {
        "chapters": ["28", "29"],                     # inorganics (e.g., SF6), organic halogenated (PFCs)
        "aliases": ["nf3", "cf4", "c2f6", "c3f6", "c4f6", "sf6", "etching gas", "fluorinated gas"],
    },
    "advanced chips": {
        "chapters": ["85"],                           # integrated circuits
        "aliases": ["sub-10nm", "5nm", "3nm", "tsmc", "samsung foundry", "leading-edge chips"],
    },

    # ── Battery components ─────────────────────────────────────────────────────
    "battery lithium": {
        "chapters": ["28"],                           # Li compounds for batteries
        "aliases": ["lithium hydroxide", "lithium carbonate", "battery-grade"],
    },
    "cathode": {
        "chapters": ["28", "38"],                     # mixed Ni/Co/Mn compounds often in 28/38
        "aliases": ["nmc", "nca", "lfp", "cathode material"],
    },
    "anode": {
        "chapters": ["28", "38"],                     # graphite/silicon-graphite blends & precursors
        "aliases": ["graphite anode", "hard carbon", "silicon-graphite"],
    },
    "separator": {
        "chapters": ["39"],                           # plastic films
        "aliases": ["separator film", "battery separator"],
    },

    # ── Pharma & resins ────────────────────────────────────────────────────────
    "api": {
        "chapters": ["29", "30"],                     # organic chemicals; medicaments
        "aliases": [
            "api", "active pharmaceutical ingredient",
            "penicillin", "heparin", "vitamin c", "ascorbic acid", "bulk pharmaceutical"
        ],
    },
    "epoxy resin": {
        "chapters": ["39"],                           # plastics (epoxy resins 3907)
        "aliases": ["epoxy", "epoxy resin", "bisphenol-a epoxy", "bpa-epoxy"],
    },

    # ── Gases & fuels ──────────────────────────────────────────────────────────
    "helium": {
        "chapters": ["28"],
        "aliases": ["helium", "he", "liquid helium"],
    },
    "neon": {
        "chapters": ["28"],
        "aliases": ["neon", "ne"],
    },
    "natural gas": {
        "chapters": ["27"],
        "aliases": ["lng", "natural gas", "pipeline gas"],
    },
    "ammonia": {
        "chapters": ["28", "31"],
        "aliases": ["ammonia", "nh3"],
    },

    # ── Metals & general ───────────────────────────────────────────────────────
    "steel": {
        "chapters": ["72", "73"],
        "aliases": ["iron", "steel", "hrc", "crc", "rebar"],
    },
    "aluminum alloy": {
        "chapters": ["76"],
        "aliases": ["aluminium alloy", "aluminum alloy"],
    },
    "neodymium magnets": {
        "chapters": ["85"],
        "aliases": ["neodymium magnets", "ndfeb", "rare earth magnets", "permanent magnets"],
    },
    "prepreg": {
        "chapters": ["68", "39"],
        "aliases": ["carbon fiber prepreg", "carbon fibre prepreg", "aerospace prepreg", "prepregs"],
    },
}

def _material_theme_boosts(cat_df: pd.DataFrame, q_norm: str) -> np.ndarray:
    boosts = np.zeros(len(cat_df), dtype=float)
    for _, cfg in MATERIAL_HINTS.items():
        if any(a in q_norm for a in cfg["aliases"]):
            if "chapters" in cfg:
                boosts += 0.04 * cat_df["hs_chapter"].isin(cfg["chapters"]).to_numpy(dtype=float)
            pattern = r'(?:' + '|'.join(map(re.escape, cfg["aliases"])) + r')\b'
            boosts += 0.03 * cat_df["name_norm"].str.contains(pattern, regex=True, na=False).to_numpy(dtype=float)
    return boosts

CAT = None
VECT = None
X = None
NAME_NORM = None

def normalize_text(s: str) -> str:
    s = s or ""
    s = unidecode(s).strip().lower()
    s = re.sub(r"\s+", " ", s)
    return s

def _query_hints(q_norm: str):
    tokens = set(q_norm.split())
    is_copper = any(k in tokens for k in COPPER_KEYWORDS) or "copper" in q_norm
    subtypes = {label for label, keys in SUBTYPE_HINTS.items() if any(k in q_norm for k in keys)}
    return is_copper, subtypes

def _build_catalog(fetch_df):
    # ---------------------------------------------------------------------------------------------------------------------------------------------------
    # --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
    # ---------------------------------------------------------------------------------------------------------------------------------------------------
    kb = fetch_df('SELECT * FROM knowledge_base').fillna('')
    t1 = fetch_df('SELECT [Input Product] AS name, [Percentage Cost] FROM tier_1_input_products').fillna('')
    t2 = fetch_df('SELECT [Input Product] AS name, [Percentage Cost] FROM tier_2_input_products').fillna('')
    finals = fetch_df('SELECT [Product Name] AS name FROM company_main_products').fillna('')
    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    rows = []
    # Knowledge base terms + synonym
    for _, r in kb.iterrows():
        terms = [r.get('Term', '')]
        syn = r.get('Synonyms', '')
        if syn:
            # This is to support comma or semicolon separated synonyms
            terms += [s.strip() for s in re.split(r'[;,]', syn) if s.strip()]
        for term in terms:
            if term:
                rows.append({
                    'name': term,
                    'source': 'kb',
                    'hs_code': r.get('HS_Codes', ''),
                    'type': r.get('Type', '')
                })

    rows += [{'name': n, 'source': 'tier1', 'hs_code': '', 'type': ''} for n in t1['name'].tolist() if n]
    rows += [{'name': n, 'source': 'tier2', 'hs_code': '', 'type': ''} for n in t2['name'].tolist() if n]
    rows += [{'name': n, 'source': 'final', 'hs_code': '', 'type': ''} for n in finals['name'].tolist() if n]

    cat = pd.DataFrame(rows).drop_duplicates(subset=['name']).reset_index(drop=True)
    cat['name_norm'] = cat['name'].map(normalize_text)
    cat['material'] = cat['name_norm'].str.extract(r'\b(copper|aluminum|iron|steel|nickel|zinc|lead|tin)\b', expand=False).fillna('')
    cat['hs_chapter'] = cat['hs_code'].astype(str).str.extract(r'^(\d{2})', expand=False).fillna('')
    return cat

def init_resolver(fetch_df):
    global CAT, VECT, X, NAME_NORM
    CAT = _build_catalog(fetch_df)
    NAME_NORM = CAT['name_norm'].tolist()
    VECT = TfidfVectorizer(ngram_range=(1, 2), min_df=1, norm='l2')
    X = VECT.fit_transform(NAME_NORM)

# Rule based filtering
def apply_subtype_hard_filter(df: pd.DataFrame, q_norm: str) -> pd.DataFrame:
    rules = [
        (r'\b(ore|concentrate|concentrates)\b', 'ore'),
        (r'\boxide|hydroxide|oxides|hydroxides\b', 'oxide'),
        (r'\bscrap|waste\b', 'scrap'),
        (r'\bwire|winding\b', 'wire'),
        (r'\bfoil\b', 'foil'),
        (r'\bscrew|bolt|nut|washer|rivets|cotter\b', 'fastener'),
        (r'\bwafer|wafers|epitaxial\b', 'wafers'),
        (r'\bmagnets?|ndfeb|rare earth magnets\b', 'magnets'),
        (r'\bapi|active pharmaceutical\b', 'api'),
        (r'\bepoxy|resin\b', 'resin'),
        (r'\balloy|alloys\b', 'alloy'),
        (r'\bseparator( film)?s?\b', 'separator'),
        (r'\bcathode|anode\b', 'electrode'),
        (r'\blithography|euv|duv\b', 'lithography'),
    ]
    for pattern, _ in rules:
        if re.search(pattern, q_norm):
            return df[df['name_norm'].str.contains(pattern)]
    return df

def resolve_products(user_text: str, k: int = 10, min_score: float = 0.45, hard_filter: bool = False):
    """Lean resolver: TF-IDF cosine + fuzzy + domain boosts."""
    assert CAT is not None and VECT is not None and X is not None, "Call init_resolver(fetch_df) first."
    q = normalize_text(user_text)
    is_copper, subtypes = _query_hints(q)
    # 1) TF-IDF cosine
    q_vec = VECT.transform([q])
    cos = (X @ q_vec.T).toarray().ravel()

    # 2) Fuzzy token-set ratio
    fz = np.array([fuzz.token_set_ratio(q, s) / 100.0 for s in NAME_NORM], dtype=float)

    # 3) Domain boosts
    boost = np.zeros(len(CAT), dtype=float)
    if is_copper:
        boost += 0.06 * CAT['name_norm'].str.contains(r'\bcopper\b').to_numpy(dtype=float)
        boost += 0.05 * CAT['hs_chapter'].eq('74').to_numpy(dtype=float)  # copper HS chapter

    for label in subtypes:
        keys = SUBTYPE_HINTS[label]
        mask = CAT['name_norm'].str.contains(r'(' + '|'.join(map(re.escape, keys)) + r')\b')
        boost += 0.04 * mask.to_numpy(dtype=float)

    boost += _material_theme_boosts(CAT, q)

    # 4) Final score for result (we're giving TF-IDF the most weight)
    score = 0.70 * cos + 0.20 * fz + boost

    df = CAT[['name', 'name_norm', 'hs_code', 'hs_chapter', 'type', 'source', 'material']].copy()
    df['score'] = score

    if hard_filter:
        df = apply_subtype_hard_filter(df, q)

    df = df[df['score'] >= min_score].sort_values('score', ascending=False).head(k)

    # 5) Remove near-duplicates
    kept, seen = [], []
    for _, r in df.iterrows():
        n = r['name_norm']
        if not any(fuzz.token_set_ratio(n, s) >= 92 for s in seen):
            kept.append(r)
            seen.append(n)
    return pd.DataFrame(kept).reset_index(drop=True)

def trace_from_user_text(user_text: str, trace_supply_chain_fn, depth: int = 2,
                              top_n: int = 3, cutoff: float = 0.50, hard_filter: bool = False):
    cands = resolve_products(user_text, k=10, min_score=cutoff, hard_filter=hard_filter)
    if cands.empty:
        return {'error': f'No product candidates found for "{user_text}". Try being more specific (e.g., copper wire / copper scrap / copper oxide).'}

    results = []
    for _, r in cands.head(top_n).iterrows():
        prod = r['name']
        trace = trace_supply_chain_fn(prod, depth=depth)
        if not (isinstance(trace, dict) and 'error' in trace):
            results.append({
                'matched_product': prod,
                'hs_code': r['hs_code'],
                'type': r['type'],
                'score': float(r['score']),
                'trace': trace
            })

    if not results:
        return {
            'query': user_text,
            'message': f'Found candidates but no paths within depth={depth}.',
            'candidates': cands[['name', 'hs_code', 'type', 'score']].to_dict(orient='records')
        }

    return {
        'query': user_text,
        'results': results,
        'candidates_shown': cands[['name', 'hs_code', 'type', 'score']].head(top_n).to_dict(orient='records')
    }
