# Configuration for Custom GPT MCP Tools

This file contains configuration settings for the MCP tools and GPT integration.

## MCP Tool Registry

```yaml
tools:
  xmetric:
    handler: "tools.xmetric.handle_xmetric"
    schema: "schemas/xmetric.schema.json"
    manifest: "mcp/xmetric_manifest.json"
    description: "Primary time-series analysis with aggregation and scaling"
    
  ymetric:
    handler: "tools.ymetric.handle_ymetric" 
    schema: "schemas/ymetric.schema.json"
    manifest: "mcp/ymetric_manifest.json"
    description: "Secondary metrics and cross-sectional analysis"
    
  portfolio_upload:
    handler: "tools.file_upload.handle_portfolio_upload"
    schema: "schemas/portfolio.schema.json"
    manifest: "mcp/portfolio_manifest.json"
    description: "Portfolio file upload and normalization"
```

## GPT Configuration

```yaml
gpt_config:
  name: "Financial Analytics GPT"
  description: "Specialized GPT for portfolio analysis, time-series metrics, and data visualization using MCP tools"
  
  capabilities:
    - "Portfolio analysis and risk assessment"
    - "Time-series metric computation (XMetric, YMetric)"
    - "Interactive chart generation"
    - "Financial document search and analysis"
    - "Structured data processing"
  
  data_sources:
    file_search: 
      corpus_size: "~10MB"
      content_types: ["earnings", "news", "filings", "market_data"]
    web_search: 
      enabled: true
      fallback_only: true
    user_uploads:
      formats: ["csv", "xlsx"]
      session_only: true
      
  performance_targets:
    response_time: "< 3 seconds"
    first_token: "< 1 second"
    
  conversation_starters:
    - "Upload my portfolio and run risk analysis"
    - "Run XMetric analysis on sample market data"  
    - "Create scatter plot comparing XMetric vs YMetric"
    - "Explain drought impact on agricultural sector"
    - "Generate executive summary with key charts"
```

## Chart Specifications

```yaml
chart_types:
  time_series:
    artifact_type: "line_chart"
    required_fields: ["date", "value"]
    optional_fields: ["label", "series"]
    
  scatter_plot:
    artifact_type: "scatter_plot" 
    required_fields: ["x", "y"]
    optional_fields: ["label", "size", "color"]
```

## File Paths

```yaml
paths:
  data_root: "data/"
  schema_root: "schemas/"
  mcp_root: "mcp/"
  eval_root: "data/eval/"
  upload_temp: "/tmp/uploads/"  # For future app migration
```