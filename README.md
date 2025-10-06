# Financial Analytics Custom GPT

A production-ready **Custom GPT** with **MCP (Model Context Protocol)** integration for portfolio analysis, time-series metrics, and financial data visualization. Built for **speed, accuracy, and extensibility**.

## 🎯 **Project Overview**

This GPT integrates two table-based metrics (**XMetric**, **YMetric**) as MCP tools, supports portfolio uploads, uses File Search for financial document analysis, and generates interactive charts using GPT's built-in artifact rendering.

**Key Features:**
- 🔧 **MCP Tools**: XMetric/YMetric for time-series and cross-sectional analysis
- 📊 **Chart Generation**: Time series & scatter plots via GPT artifacts
- 📁 **Portfolio Upload**: CSV/XLSX normalization and validation
- 🔍 **RAG Integration**: File Search (~10MB corpus) + web search fallback
- ⚡ **Performance**: <3s responses, <1s first token
- 🏗️ **Migration-Ready**: Structured for future standalone app

## 🚀 **Quick Start**

### 1. Install Dependencies
```bash
poetry install
```

### 2. Test Implementation
```bash
poetry run python data/eval/comprehensive_eval.py
```

### 3. Configure Custom GPT
Follow the detailed setup guide in [`SETUP.md`](SETUP.md)

## 📁 **Project Structure**

```
/gpt                    # GPT Configuration
  system_prompt.md      # Complete system prompt (copy to GPT)
  prompt_cards.md       # Conversation starters

/tools                  # MCP Tool Implementations  
  xmetric.py           # Primary time-series analysis
  ymetric.py           # Secondary metrics analysis
  file_upload.py       # Portfolio upload & normalization
  chart_utils.py       # Chart generation for GPT artifacts
  __init__.py          # Package initialization

/mcp                    # MCP Tool Manifests
  xmetric_manifest.json    # XMetric tool specification
  ymetric_manifest.json    # YMetric tool specification  
  portfolio_manifest.json # Portfolio tool specification

/schemas                # JSON Schema Validation
  xmetric.schema.json     # XMetric input validation
  ymetric.schema.json     # YMetric input validation
  portfolio.schema.json   # Portfolio data validation

/models                 # API Layer (for future migration)
  api.py               # FastAPI wrappers

/data                   # Data & Evaluation
  sample.csv           # Test time-series data
  /eval               # Evaluation scripts
    run_eval.py        # Basic tool testing
    comprehensive_eval.py # Full system validation

config.md              # Configuration documentation
SETUP.md              # Detailed GPT setup instructions
```

## 🔧 **Core Tools**

### XMetric Tool
- **Purpose**: Primary time-series analysis with aggregation and scaling
- **Input**: Table name, date column, value column, aggregation method, scale factor
- **Output**: Time series data + statistical summary
- **Use Cases**: Stock price analysis, performance metrics, trend analysis

### YMetric Tool  
- **Purpose**: Secondary metrics and cross-sectional analysis
- **Input**: Same as XMetric but optimized for comparative analysis
- **Output**: Processed metrics suitable for correlation/comparison
- **Use Cases**: Risk metrics, sector comparisons, relative performance

### Portfolio Upload Tool
- **Purpose**: Portfolio file processing and normalization
- **Input**: CSV/XLSX files with ticker/weight columns
- **Output**: Normalized portfolio data (weights sum to 1.0)
- **Use Cases**: Portfolio analysis, risk assessment, rebalancing

## 📊 **Chart Generation**

### Time Series Charts
```json
{
  "type": "line_chart",
  "data": [{"date": "2024-01-01", "value": 100.5}],
  "title": "Metric Analysis Over Time"
}
```

### Scatter Plots
```json
{
  "type": "scatter_plot", 
  "data": [{"x": 1.2, "y": 3.4, "label": "AAPL"}],
  "title": "XMetric vs YMetric Analysis"
}
```

## 🧪 **Testing & Validation**

### Run Full Evaluation
```bash
poetry run python data/eval/comprehensive_eval.py
```

**Tests Include:**
- ✅ Tool input/output validation
- ✅ JSON schema compliance
- ✅ Chart generation
- ✅ Portfolio processing
- ✅ Project structure validation
- ✅ API endpoint testing (if running)

### Individual Tool Testing
```bash
poetry run python data/eval/run_eval.py
```

## 🎯 **Performance Targets** 

- **Response Time**: < 3 seconds total
- **First Token**: < 1 second  
- **Tool Execution**: < 500ms per tool
- **Chart Generation**: < 200ms
- **File Processing**: < 1 second for typical portfolios

## 🏗️ **Migration Path**

### Current: Custom GPT
- MCP tools simulate via structured prompts
- File Search for document retrieval
- GPT artifact rendering for charts
- Session-only portfolio storage

### Future: Standalone App
- FastAPI wrappers around existing tools
- Persistent user data and portfolios
- Custom frontend with enhanced visualizations
- Full authentication and multi-tenancy

**Migration Command Preview:**
```bash
# Future migration to standalone app
poetry add fastapi uvicorn sqlalchemy alembic
# Tools are already API-ready!
```

## 🔐 **Security & Best Practices**

- ✅ **Input Validation**: Pydantic models + JSON Schema
- ✅ **Error Handling**: Comprehensive exception management  
- ✅ **Type Safety**: Full typing throughout codebase
- ✅ **Separation of Concerns**: Clean architecture patterns
- ✅ **Stateless Design**: No cross-request dependencies
- ✅ **Schema Versioning**: Future-proof data contracts

## 📚 **Documentation**

- [`SETUP.md`](SETUP.md) - Detailed GPT configuration guide
- [`config.md`](config.md) - Configuration reference
- [`gpt/system_prompt.md`](gpt/system_prompt.md) - Complete system prompt
- [`gpt/prompt_cards.md`](gpt/prompt_cards.md) - Conversation starters

## 🤝 **Contributing**

### Adding New Tools
1. Create tool handler in `/tools/`
2. Define JSON schema in `/schemas/`
3. Create MCP manifest in `/mcp/`
4. Add tests to evaluation scripts
5. Update GPT system prompt

### Extending Schemas
- Add optional fields by default
- Maintain backward compatibility
- Version schemas when breaking changes needed
- Update validation in tool handlers

## 📄 **License**

MIT License - Built for the future of AI-powered financial analysis.

---

