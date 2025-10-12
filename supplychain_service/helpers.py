
import yfinance as yf
import pandas as pd
import networkx as nx
import json
from sentence_transformers import SentenceTransformer, util

from config import (
    COMPANY_MAIN_PRODUCTS_FILE,
    TIER_1_INPUT_PRODUCTS_FILE,
    TIER_2_INPUT_PRODUCTS_FILE,
    TIER_1_LOCATIONS_FILE,
    TIER_2_LOCATIONS_FILE
)

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
# ---------------------------------------------------------------------------------------------------------------------------------------------------
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'supply_chain.db')

def get_db_connection():
    return sqlite3.connect(DB_PATH)

def fetch_df(query, params=None):
    import pandas as pd
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(query, conn, params=params or {})
        return df
    finally:
        conn.close()

# ---------------------------------------------------------------------------------------------------------------------------------------------------
# --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
# ---------------------------------------------------------------------------------------------------------------------------------------------------
from flask_login import current_user
from openai import OpenAI

def get_openai_client():
    """Get OpenAI client using current user's API key"""
    if not current_user or not current_user.api_key:
        raise ValueError("No API key found for current user")
    return OpenAI(api_key=current_user.api_key)

def chat_with_gpt(user_input: str, history=None, functions=None):
    """Chat with GPT using the current user's API key"""
    if history is None:
        history = []
    
    client = get_openai_client()
    
    # Build conversation history
    messages = list(history)
    if user_input:
        messages.append({"role": "user", "content": user_input})
    
    # Prepare function calling if specified
    kwargs = {
        "model": "gpt-4-1106-preview",
        "messages": messages,
        "max_tokens": 1500,
        "temperature": 0.7,
    }
    
    if functions:
        kwargs["functions"] = functions
        kwargs["function_call"] = "auto"
    else:
        # For scenario tracing, we want structured function calls
        kwargs["functions"] = FUNCTION_DEFINITIONS
        kwargs["function_call"] = "auto"
    
    try:
        response = client.chat.completions.create(**kwargs)
        
        message = response.choices[0].message
        
        # Check if GPT called a function
        if hasattr(message, 'function_call') and message.function_call:
            function_name = message.function_call.name
            function_args = json.loads(message.function_call.arguments)
            
            # Execute the function
            if function_name == "get_stock_history":
                result = get_stock_history(**function_args)
                return message.content or "", result, "stock_chart"
            elif function_name == "get_products_by_company":
                result = get_products_by_company(**function_args)
                return message.content or "", result.to_dict('records'), "company_products"
            elif function_name == "trace_supply_chain":
                result = trace_supply_chain(**function_args)
                return message.content or "", result, "supply_chain_trace"
            elif function_name == "scenario_trace":
                result = scenario_trace(**function_args)
                return message.content or "", result, "scenario_analysis"
        
        return message.content, None, None
        
    except Exception as e:
        raise Exception(f"OpenAI API error: {str(e)}")
# ---------------------------------------------------------------------------------------------------------------------------------------------------

# ──────────────────────────── Functions that LLM can use ────────────────────────────────
FUNCTION_DEFINITIONS = [
    {
        "name": "get_stock_history",
        "description": "Fetch historical OHLCV data for a stock ticker",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "Stock symbol, e.g. TSLA"},
                "period": {
                    "type": "string",
                    "enum": ["1d","5d","1mo","3mo","6mo","1y","2y","5y","10y","ytd","max"],
                    "description": "Data range to fetch", "default": "1y"
                },
                "interval": {
                    "type": "string",
                    "enum": ["1d","1wk","1mo","1h","30m","15m"],
                    "description": "Granularity of data", "default": "1d"
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "get_products_by_company",
        "description": (
            "Retrieve the list of main products manufactured or sold by a company. "
            "Internally this uses the master table mapping each ticker to its key product lines. "
            "Returns a list of records, each including columns like: "
            "Company ticker, Company name, Product name, HS code, Industry name, Industry code, and % of company revenue or production represented by that product. "
            "If the company isn't found, returns an empty list."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "The company's stock ticker, e.g. 'MSFT'."
                }
            },
            "required": ["ticker"]
        }
    },
    {
        "name": "trace_supply_chain",
        "description": (
            "Perform a multi‐tier supply chain trace for a given input material. "
            "This function now supports multi-path tracing and returns causal chains. "
            "It can trace the supply chain for any given product and depth. "
            "Returns an object with these keys: "
            "product (input name), trace_depth, causal_chains (a list of traced paths), "
            "and a narrative_summary of the findings. "
            "On failure (e.g., unknown input) returns {'error': '…'}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "product": {
                    "type": "string",
                    "description": "Name of the raw material or intermediate input to trace, e.g. 'cobalt oxides and hydroxides'."
                },
                "depth": {
                    "type": "integer",
                    "description": "The depth of the supply chain trace. Default is 2.",
                    "default": 2
                }
            },
            "required": ["product"]
        }
    },
    {
        "name": "scenario_trace",
        "description": "Traces the supply chain impact from a given shock event, commodity, or location.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The shock to trace, which can be an event (e.g., 'drought'), a commodity (e.g., 'wheat'), or a location (e.g., 'Taiwan')."
                },
                "depth": {
                    "type": "integer",
                    "description": "The depth of the supply chain trace. Default is 2.",
                    "default": 2
                }
            },
            "required": ["query"]
        }
    }
]

# ──────────────────────────── Artifact-related Helper Functions ────────────────────────────────

def get_stock_history(ticker: str, period: str = "1y", interval: str = "1d"):
    ticker = ticker.upper()
    stock  = yf.Ticker(ticker)
    hist   = stock.history(period=period, interval=interval)

    if hist.empty:
        print(f"[Warning] No data for {ticker}")

    hist = hist.reset_index()
    hist['Date'] = hist['Date'].dt.strftime('%Y-%m-%d')

    prices = hist[['Date', 'Close']].to_dict(orient='records')

    return {
        "sub_type": "stock_prices",
        "prices": prices,
        "xKey": "Date",
        "yKey": "Close",
        "ticker": ticker,
        "period": period,
        "interval": interval
    }

def get_products_by_company(ticker: str):
    df = pd.read_csv(COMPANY_MAIN_PRODUCTS_FILE)
    out = df[df["Ticker"] == ticker].copy()
    if 'share_pct' in out.columns:
        out['share_pct'] = (
            out['share_pct'].astype(str)
            .str.replace('%', '', regex=False)
            .str.replace(',', '', regex=False)
            .str.strip()
        )
        out['share_pct'] = pd.to_numeric(out['share_pct'], errors='coerce')
    return out

def trace_supply_chain(product: str, depth: int = 2, portfolio_path: str = None):
    product = product.strip().lower()
    
    # 1) Load all data from SQLite
    # ---------------------------------------------------------------------------------------------------------------------------------------------------
    # --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
    # ---------------------------------------------------------------------------------------------------------------------------------------------------
    company_main_products_df = fetch_df('SELECT * FROM company_main_products').fillna('')
    tier_1_input_products_df = fetch_df('SELECT * FROM tier_1_input_products').fillna('')
    tier_2_input_products_df = fetch_df('SELECT * FROM tier_2_input_products').fillna('')
    tier_1_locations_df = fetch_df('SELECT * FROM tier_1_locations').fillna('')
    tier_2_locations_df = fetch_df('SELECT * FROM tier_2_locations').fillna('')
    # ---------------------------------------------------------------------------------------------------------------------------------------------------


    # 2) Create a directed graph
    G = nx.DiGraph()

    # Add nodes and edges from Tier 2 to Tier 1
    for _, row in tier_2_input_products_df.iterrows():
        cost = row['Percentage Cost']
        if pd.isna(cost):
            cost = None
        G.add_edge(row['Input Product'].lower(), row['Main Product Name'].lower(), percentage_cost=cost)

    # Add nodes and edges from Tier 1 to Main Products
    for _, row in tier_1_input_products_df.iterrows():
        cost = row['Percentage Cost']
        if pd.isna(cost):
            cost = None
        G.add_edge(row['Input Product'].lower(), row['Main Product Name'].lower(), percentage_cost=cost)

    # Add company information to nodes
    # Add company information to nodes
    for _, row in company_main_products_df.iterrows():
        node_name = row['Product Name'].lower()
        if node_name in G:
            ticker = row['Ticker'] if not pd.isna(row['Ticker']) else None
            industry = row['Industry'] if not pd.isna(row['Industry']) else None
            
            G.nodes[node_name].setdefault('companies', [])
            if ticker and ticker not in G.nodes[node_name]['companies']:
                G.nodes[node_name]['companies'].append(ticker)
            G.nodes[node_name]['industry'] = industry

            # Adding share_pct
            if 'share_pct' in row and pd.notna(row['share_pct']) and ticker:
                G.nodes[node_name].setdefault('share_pct_by_company', {})
                G.nodes[node_name]['share_pct_by_company'][ticker] = float(row['share_pct'])

    # 3) Trace the supply chain
    if not G.has_node(product):
        return {'error': f'Product "{product}" not in graph'}

    # Find all leaf nodes (nodes with out_degree 0) which are the final products
    leaf_nodes = [node for node, out_degree in G.out_degree() if out_degree == 0]

    all_paths = []
    for target_node in leaf_nodes:
        try:
            # Check if a path exists before calling all_simple_paths
            if nx.has_path(G, product, target_node):
                paths = list(nx.all_simple_paths(G, source=product, target=target_node, cutoff=depth))
                all_paths.extend(paths)
        except nx.NodeNotFound:
            # This can happen if the source product is not in the graph, handled above.
            # Or if target_node is somehow not in the graph, which shouldn't happen with this logic.
            continue

    if not all_paths:
        return {'error': f'No supply chain paths found for "{product}" within depth {depth}.'}

    causal_chains = []
    nodes = {}
    edges = []
    node_counter = 1
    for path in all_paths:
        chain = []
        for i in range(len(path)):
            node_name = path[i]
            node_id = f"node_{node_counter}"
            node_counter += 1
            node_type = 'product' if i == 0 else ('company' if i == len(path)-1 else 'intermediate')
            share_map = G.nodes.get(node_name, {}).get('share_pct_by_company', {})
            node_data = {
                "id": node_id,
                "label": node_name,
                "type": node_type,
                "industry": G.nodes.get(node_name, {}).get('industry', 'N/A'),
                "companies": G.nodes.get(node_name, {}).get('companies', ['N/A']),
                "share_pct_by_company": share_map,
                "location": G.nodes.get(node_name, {}).get('location', None),
                "lat": G.nodes.get(node_name, {}).get('lat', None),
                "lng": G.nodes.get(node_name, {}).get('lng', None)
            }
            nodes[node_id] = node_data
            if i > 0:
                prev_node_id = f"node_{node_counter-2}"
                edge_data = G.get_edge_data(path[i-1], node_name)
                cost_value = edge_data.get('percentage_cost', 'N/A') if edge_data else 'N/A'
                edges.append({
                    "from": prev_node_id,
                    "to": node_id,
                    "label": edge_data.get('product_link', '') if edge_data else '',
                    "effect_type": 'Direct' if i == 1 else 'Indirect',
                    "cost_impact": cost_value
                })
            # For pop-up data
            popup = {}
            if node_type == 'product':
                popup = {"name": node_name, "produced_by": node_data["companies"]}
            elif node_type == 'company':
                popup = {"name": node_name, "input_product": path[0], "effect_type": 'Direct' if i == 1 else 'Indirect', "cost_impact": cost_value}
            else:
                popup = {"name": node_name, "input_output": f"{path[i-1]} → {node_name}"}
            node_data["popup"] = popup
            chain.append(node_data)
        if chain:
            causal_chains.append(chain)

    # 4) Calculate portfolio exposure
    portfolio_exposure = {}
    if portfolio_path:
        with open(portfolio_path, 'r') as f:
            portfolio = json.load(f)
            portfolio_tickers = {ticker['ticker']: ticker['weight'] for ticker in portfolio['holdings']}
            
            for chain in causal_chains:
                for step in chain:
                    # Access companies from the new node structure
                    companies = step.get('companies', [])
                    if isinstance(companies, list):
                        for company in companies:
                            if company and company != 'N/A' and company in portfolio_tickers:
                                if company not in portfolio_exposure:
                                    portfolio_exposure[company] = {'weight': portfolio_tickers[company], 'chains': []}
                                portfolio_exposure[company]['chains'].append(chain)

    # 5) Generate narrative summary
    narrative_summary = generate_narrative_summary(product, causal_chains, portfolio_exposure)

    return {
        'product': product,
        'trace_depth': depth,
        'causal_chains': causal_chains,
        'nodes': list(nodes.values()),
        'edges': edges,
        'portfolio_exposure': portfolio_exposure,
        'narrative_summary': narrative_summary
    }

def generate_narrative_summary(product, causal_chains, portfolio_exposure=None):
    if not causal_chains:
        return f"No supply chain paths found for {product}."
    summary = f"Supply chain analysis for **{product}** reveals the following key paths:\n\n"
    for i, chain in enumerate(causal_chains[:5]):  # Limit to 5 paths for brevity
        summary += f"**Path {i+1}:**\n"
        path_parts = []
        for step in chain:
            # Use the label (node name) and first company if available
            company_str = f" ({step.get('companies', ['N/A'])[0]})" if step.get('companies') and step.get('companies')[0] != 'N/A' else ""
            path_parts.append(f"{step['label']}{company_str}")
        path_str = " → ".join(path_parts)
        summary += f"*   {path_str}\n"
        # Calculate cost impact from edges if available
        total_cost_impact = 1
        for j, step in enumerate(chain):
            if j > 0:  # Skip first node (no incoming edge)
                # Try to get cost from popup data or default
                cost = step.get('popup', {}).get('cost_impact', 0)
                if isinstance(cost, (int, float)) and cost != 'N/A':
                    total_cost_impact *= (cost / 100.0)
        summary += f"*   **Estimated Cost Impact on Final Product:** {total_cost_impact:.2%}\n"
        summary += f"*   **Final Industry:** {chain[-1].get('industry', 'N/A')}\n\n"
    if len(causal_chains) > 5:
        summary += f"And {len(causal_chains) - 5} more paths.\n"
    if portfolio_exposure:
        summary += "\n**Portfolio Exposure:**\n"
        for ticker, data in portfolio_exposure.items():
            summary += f"*   **{ticker}:** {data['weight']}% of portfolio. Exposed through {len(data['chains'])} supply chain(s).\n"

# ──────────────────────────── Scenario Tracing-related Helper Functions ────────────────────────────────
# def clean_nan_from_json(obj):
#     if isinstance(obj, dict):
#         return {k: clean_nan_from_json(v) for k, v in obj.items() if not _is_nan(v)}
#     elif isinstance(obj, list):
#         return [clean_nan_from_json(elem) for elem in obj if not _is_nan(elem)]
#     elif _is_nan(obj):
#         return None
#     return obj

# def _is_nan(x):
#     # Handles scalars, arrays, Series, etc.
#     try:
#         val = pd.isna(x)
#         if isinstance(val, (bool, type(None))):
#             return val
#         # If val is an array/Series, treat as nan if all elements are nan
#         if hasattr(val, 'all'):
#             return val.all()
#         return bool(val)
#     except Exception:
#         return False

def resolve_term_to_codes(term: str):
    """Resolves a natural language term to a list of relevant codes using the SQLite DB."""
    # -------------------------------- To be turned into real db calls --------------------------------
    knowledge_base_df = fetch_df('SELECT * FROM knowledge_base')
    # -------------------------------- To be turned into real db calls --------------------------------
    model = SentenceTransformer('all-MiniLM-L6-v2')

    term_embedding = model.encode(term, convert_to_tensor=True)
    
    best_match = None
    max_similarity = -1

    for index, row in knowledge_base_df.iterrows():
        synonyms = row['Synonyms']
        if pd.isna(synonyms):
            synonyms = ''
        phrases = [row['Term']] + (synonyms.split(',') if synonyms else [])
        for phrase in phrases:
            phrase_embedding = model.encode(phrase.strip(), convert_to_tensor=True)
            similarity = util.pytorch_cos_sim(term_embedding, phrase_embedding).item()
            if similarity > max_similarity:
                max_similarity = similarity
                best_match = row

    if best_match is not None and max_similarity > 0.5: # Threshold for a good match
        return {
            "type": best_match['Type'],
            "hs_codes": [code.strip() for code in str(best_match['HS_Codes']).split(',')] if pd.notna(best_match['HS_Codes']) else [],
            "product_codes": [code.strip() for code in str(best_match['Product_Codes']).split(',')] if pd.notna(best_match['Product_Codes']) else [],
            "industry_codes": [code.strip() for code in str(best_match['Industry_Codes']).split(',')] if pd.notna(best_match['Industry_Codes']) else []
        }
    return {}

# def generate_holistic_narrative(scenario, results, client, affected_companies=None):
#     """Generates a holistic narrative summary using an LLM."""
    
#     # Filter out empty results and extract key information
#     valid_results = [r for r in results if r and not r.get('error')]
#     if not valid_results:
#         return "No significant supply chain impacts were identified for this scenario."

#     # Consolidate all causal chains and portfolio exposures
#     all_causal_chains = []
#     all_portfolio_exposures = {}
#     for res in valid_results:
#         all_causal_chains.extend(res.get('causal_chains', []))
#         for ticker, data in res.get('portfolio_exposure', {}).items():
#             if ticker not in all_portfolio_exposures:
#                 all_portfolio_exposures[ticker] = data
#             else:
#                 # Combine chains and ensure weight is consistent
#                 all_portfolio_exposures[ticker]['chains'].extend(data.get('chains', []))

#     # Clean NaN values before dumping to JSON
#     cleaned_causal_chains = clean_nan_from_json(all_causal_chains)
#     cleaned_affected_companies = clean_nan_from_json(affected_companies)
#     cleaned_portfolio_exposures = clean_nan_from_json(all_portfolio_exposures)

#     # Create a detailed prompt for the LLM
#     prompt = f"""
#     As a senior financial analyst, provide a comprehensive analysis of the following scenario: **{scenario}**

#     **Structured Data Analysis:**

#     **Direct Causal Chains:**
#     {json.dumps(cleaned_causal_chains, indent=2)}

#     **Exposed Companies:**
#     {json.dumps(cleaned_affected_companies, indent=2)}

#     **Portfolio Exposure:**
#     {json.dumps(cleaned_portfolio_exposures, indent=2)}

#     **Analysis Request:**

#     Based on the structured data above, please generate a professional, data-driven narrative report. The report should:

#     1.  **Executive Summary:** Start with a brief overview of the key findings and the overall impact of the scenario.
#     2.  **Direct Impact Analysis:** Analyze the direct impact on the traced commodities and their immediate downstream supply chains.
#     3.  **Broader Business Implications:** For the exposed companies, infer the broader strategic and financial implications. Consider their overall business models, other product lines, and potential vulnerabilities beyond the directly traced supply chains.
#     4.  **Financial Impact Assessment:** Assess the potential financial impact on the companies and industries involved. Discuss potential revenue loss, cost increases, and margin compression.
#     5.  **Portfolio Impact Analysis:** Analyze the impact on the investment portfolio. Identify the most exposed positions and quantify the potential risks.
#     6.  **Forward-Looking Perspective:** Provide a forward-looking perspective on the long-term implications of the scenario. Discuss potential mitigating actions that companies and investors could take.

#     Please structure your response as a professional report, using clear headings and a data-driven approach.
#     """

#     # ---------------------------------------------------------------------------------------------------------------------------------------------------
#     # --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
#     # ---------------------------------------------------------------------------------------------------------------------------------------------------
#     try:
#         response = client.chat.completions.create(
#             model="gpt-4.1-2025-04-14",
#             messages=[{"role": "system", "content": prompt}],
#             max_tokens=1500,
#             temperature=0.7,
#         )
#         return response.choices[0].message.content
#     except Exception as e:
#         return f"Error generating narrative: {e}"
#     # ---------------------------------------------------------------------------------------------------------------------------------------------------

def scenario_trace(query: str, depth: int = 2, portfolio_path: str = None):
    """Traces the supply chain impact from a given shock event, commodity, or location using the SQLite DB."""
    query = query.strip().lower()

    # ---------------------------------------------------------------------------------------------------------------------------------------------------
    # --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
    # ---------------------------------------------------------------------------------------------------------------------------------------------------
    client = get_openai_client()
    # ---------------------------------------------------------------------------------------------------------------------------------------------------

    # Use the semantic resolver to understand the query
    codes = resolve_term_to_codes(query)
    
    # Default to commodity if no specific type is identified
    shock_type = codes.get("type", "commodity")

    # Route to appropriate logic
    if shock_type == 'event':
        # ---------------------------------------------------------------------------------------------------------------------------------------------------
        # --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
        # ---------------------------------------------------------------------------------------------------------------------------------------------------
        event_df = fetch_df('SELECT * FROM event_to_commodity')
        company_main_products_df = fetch_df('SELECT * FROM company_main_products')
        # ---------------------------------------------------------------------------------------------------------------------------------------------------
        if 'share_pct' in company_main_products_df.columns:
            # strip %, commas, and coerce to float
            company_main_products_df['share_pct'] = (
                company_main_products_df['share_pct']
                .astype(str).str.replace('%', '', regex=False).str.replace(',', '', regex=False).str.strip()
            )
            company_main_products_df['share_pct'] = pd.to_numeric(company_main_products_df['share_pct'], errors='coerce')

        
        commodities = event_df[event_df['Event'].str.lower() == query]['Commodity'].tolist()
        
        all_results = []
        affected_companies = set()
        for commodity in commodities:
            result = trace_supply_chain(commodity, depth, portfolio_path)
            all_results.append(result)
            if not result.get('error'):
                for chain in result.get('causal_chains', []):
                    for step in chain:
                        # Access companies from the new node structure
                        companies = step.get('companies', [])
                        if isinstance(companies, list):
                            for company in companies:
                                if company and company != 'N/A':
                                    affected_companies.add(company)

        # Generate a holistic narrative summary
        narrative_summary = None
        try:
            narrative_summary = generate_holistic_narrative(query, all_results, client, list(affected_companies))
        except:
            pass

        return {"scenario": query, "results": all_results, "narrative_summary": narrative_summary}
    
    elif shock_type == 'location':
        # ---------------------------------------------------------------------------------------------------------------------------------------------------
        # --------------------------- TO BE CHANGED: remove this import and add actual authorisation/ db calls to fetch portfolio ---------------------------
        # ---------------------------------------------------------------------------------------------------------------------------------------------------
        tier_1_locations_df = fetch_df('SELECT * FROM tier_1_locations')
        # ---------------------------------------------------------------------------------------------------------------------------------------------------
        
        products = tier_1_locations_df[tier_1_locations_df['Location'].str.lower() == query]['Product Name'].tolist()
        results = [trace_supply_chain(p, depth, portfolio_path) for p in products]
        
        affected_companies = set()
        for result in results:
            if not result.get('error'):
                for chain in result.get('causal_chains', []):
                    for step in chain:
                        # Access companies from the new node structure
                        companies = step.get('companies', [])
                        if isinstance(companies, list):
                            for company in companies:
                                if company and company != 'N/A':
                                    affected_companies.add(company)

        narrative_summary = None
        try:
            narrative_summary = generate_holistic_narrative(query, results, client, list(affected_companies))
        except:
            pass

        return {"scenario": query, "results": results, "narrative_summary": narrative_summary}

    else: # Commodity or other terms
        product_codes = codes.get('product_codes', [])
        results = []
        affected_companies = set()
        if product_codes:
            for p in product_codes:
                result = trace_supply_chain(p, depth, portfolio_path)
                results.append(result)
                if not result.get('error'):
                    for chain in result.get('causal_chains', []):
                        for step in chain:
                            # Access companies from the new node structure
                            companies = step.get('companies', [])
                            if isinstance(companies, list):
                                for company in companies:
                                    if company and company != 'N/A':
                                        affected_companies.add(company)
        else:
            result = trace_supply_chain(query, depth, portfolio_path)
            results.append(result)
            if not result.get('error'):
                for chain in result.get('causal_chains', []):
                    for step in chain:
                        # Access companies from the new node structure
                        companies = step.get('companies', [])
                        if isinstance(companies, list):
                            for company in companies:
                                if company and company != 'N/A':
                                    affected_companies.add(company)

        narrative_summary = None
        try:
            narrative_summary = generate_holistic_narrative(query, results, client, list(affected_companies))
        except:
            pass
        return {"scenario": query, "results": results, "narrative_summary": narrative_summary}