# Supply Chain Custom GPT - Context Summary

## Project Overview
Converting a FastAPI supply chain service to a Custom GPT (no-code) solution by precomputing required data files and creating appropriate system prompts.

## Original Service Capabilities
- Supply chain path analysis and risk assessment
- Company-product-location relationship mapping
- Event impact analysis and scenario modeling
- Indirect exposure computation through graph traversal
- Product similarity matching and industry exposure analysis

## Custom GPT Adaptation Strategy
- **Direct capabilities**: Basic lookups, direct relationships, simple calculations
- **Precomputed files**: Complex aggregations, graph traversals, similarity matrices
- **GPT reasoning**: Indirect exposure inference from direct relationships
- **File limits**: 128k-200k tokens per file, ID mapping for size reduction

## Generated Files Status ✅
All compact files generated in `/data/precomputed/compact/`:

### Core Relationship Files
- `paths_compact.csv` - Top supply chain paths with ID mapping
- `chains_manifest.csv` - Full node sequences for path reconstruction
- `company_exposure_compact.csv` - Company-product exposures (non-zero only)
- `industry_exposure_top.csv` - Top 3 industries per product

### Reference/Lookup Files  
- `product_aliases.csv` - Product name normalization
- `scenario_summary.csv` - Events + locations merged
- `similarity_top.csv` - Top 3 similar products per product
- `overlap_top.csv` - Top 5 company overlaps per scenario
- `string_lookups.json` - ID-to-string mappings (5 categories)
- `manifest.json` - File documentation and metadata

### Skipped Files ❌
- `indirect_exposures.csv` - Too large, GPT will infer from direct relationships
- Full/unpruned versions - Exceed token limits

## Key Technical Decisions
1. **Indirect exposures**: Skipped computation, GPT reasons over direct relationships
2. **ID mapping**: String-to-integer conversion for size reduction
3. **Top-N pruning**: Limited to most relevant records per category
4. **Merged files**: Combined related datasets (events + locations)
5. **Compact-only**: No full versions generated

## File Generation Script
`generate_precomputed.py` - Fully automated extraction and compact file generation
- Dependencies: pandas, networkx, rapidfuzz, Unidecode
- Input: Raw CSV files (company_main_products, tier_1/2_input_products, etc.)
- Output: Compact, ID-mapped files ready for Custom GPT upload

## Next Steps
1. **System Prompt Creation**: Define Custom GPT instructions for:
   - How to read ID-mapped files
   - How to infer indirect relationships
   - Supply chain analysis methodology
   - Response formatting guidelines

2. **Knowledge Base Upload**: 
   - Upload all compact CSV files
   - Upload string_lookups.json and manifest.json
   - Verify token limits (target <200k per file)

3. **Testing & Validation**:
   - Test direct relationship queries
   - Validate indirect exposure reasoning
   - Compare outputs with original FastAPI service

## File Schema Reference
### paths_compact.csv
- `root_id`, `target_id`, `path_length`, `strength_score`

### company_exposure_compact.csv  
- `company_id`, `product_id`, `exposure_score`

### industry_exposure_top.csv
- `product_id`, `industry_id`, `exposure_score`, `rank`

### scenario_summary.csv
- `scenario_id`, `type`, `linked_product_ids`, `location_ids`, `severity`

### string_lookups.json
- `products`: {id: name}
- `companies`: {id: name}  
- `industries`: {id: name}
- `locations`: {id: name}
- `events`: {id: name}

## Environment Setup
- Python 3.11.9 virtual environment
- Required packages: pandas, networkx, rapidfuzz, Unidecode
- Workspace: `c:\Python\Custom GPT\supplychain_service\`

## Current Status
- ✅ Script generation and testing complete
- ✅ Compact file generation successful
- ✅ Indirect exposures computation skipped
- 🔄 Ready for Custom GPT prompt creation and upload

---
*Generated: October 12, 2025*
*Use this summary to continue the project on any computer*