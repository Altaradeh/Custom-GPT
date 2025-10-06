# Custom GPT Setup Instructions

## Step-by-Step GPT Configuration

### 1. Create Custom GPT in ChatGPT

1. Go to ChatGPT → "Explore GPTs" → "Create a GPT"
2. Use the **Builder** mode for initial setup

### 2. Basic Configuration

**Name:** `Financial Analytics GPT`

**Description:**
```
Specialized GPT for portfolio analysis, time-series metrics, and data visualization. Integrates XMetric/YMetric MCP tools, supports portfolio uploads, and generates interactive charts. Features File Search for financial documents and web search fallback. Built for speed and accuracy in financial analysis.
```

**Instructions:** 
Copy the entire content from `gpt/system_prompt.md`

### 3. Conversation Starters
Copy these from `gpt/prompt_cards.md`:
- "Upload my portfolio and run risk analysis"
- "Run XMetric analysis on sample market data"
- "Create scatter plot comparing XMetric vs YMetric"
- "Explain drought impact on agricultural sector"

### 4. Knowledge Base (File Search)

Upload your financial corpus (~10MB):
- Earnings reports
- Market analysis documents  
- Financial news articles
- SEC filings
- Research reports

**Note:** If you don't have a corpus yet, create placeholder documents or use sample financial data.

### 5. Capabilities Configuration

Enable:
- ✅ **Web Browsing** (as fallback)
- ✅ **Code Interpreter** (for data processing)
- ✅ **File Search** (primary source)

### 6. MCP Tools Integration

Currently, OpenAI doesn't have direct MCP integration in the GPT Builder. For now:

**Option A: Simulation Mode**
- The GPT will simulate tool calls based on your instructions
- Use the tool logic in your prompts
- Reference the schemas for structured outputs

**Option B: API Wrapper (Future)**
When MCP support is available:
1. Register tools using manifests in `/mcp/`
2. Point to tool handlers in `/tools/`
3. Use schemas for validation

### 7. Testing Your GPT

1. **Upload Test Portfolio:**
   ```csv
   ticker,weight
   AAPL,0.3
   MSFT,0.25
   GOOGL,0.2
   TSLA,0.15
   NVDA,0.1
   ```

2. **Test Prompts:**
   - "Analyze this portfolio using XMetric"
   - "Create a time series chart for AAPL"
   - "Compare tech vs finance sector metrics"

3. **Validate Outputs:**
   - Structured JSON responses
   - Chart specifications for artifacts
   - Proper error handling

## Local Development & Testing

### Run Evaluation Script
```bash
poetry run python data/eval/comprehensive_eval.py
```

### Test Individual Tools
```bash
poetry run python data/eval/run_eval.py
```

### API Development (Future Migration)
```bash
# When ready to migrate to standalone app
poetry add fastapi uvicorn
# Create API wrappers in models/api.py
```

## File Structure Reference

```
/gpt                    # GPT configuration
  system_prompt.md      # Main system prompt (copy to GPT)
  prompt_cards.md       # Conversation starters

/mcp                    # MCP tool manifests (future)
  xmetric_manifest.json
  ymetric_manifest.json
  portfolio_manifest.json

/tools                  # Tool implementations
  xmetric.py           # Primary time series analysis
  ymetric.py           # Secondary metrics analysis  
  file_upload.py       # Portfolio upload handler
  chart_utils.py       # Chart generation utilities

/schemas                # JSON schemas for validation
  xmetric.schema.json
  ymetric.schema.json
  portfolio.schema.json

/data                   # Data and evaluation
  sample.csv           # Test data
  /eval               # Evaluation scripts
```

## Migration Checklist

When OpenAI adds MCP support or when moving to standalone app:

- [ ] Register MCP tools using manifests
- [ ] Set up FastAPI wrappers for tools
- [ ] Implement proper authentication
- [ ] Add persistent storage for portfolios
- [ ] Set up proper logging and monitoring
- [ ] Deploy to cloud infrastructure
- [ ] Add rate limiting and security measures

## Troubleshooting

**GPT doesn't call tools properly:**
- Check system prompt tool orchestration logic
- Verify conversation starters guide users correctly
- Test with explicit tool requests

**Charts don't render:**
- Ensure JSON structure matches GPT artifact requirements
- Test chart specifications manually
- Check data format consistency

**File Search not working:**
- Verify corpus upload completed
- Check document formats are supported
- Test with known queries first