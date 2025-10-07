# Long-Term Financial Market Simulation API

A production-ready FastAPI application that serves pre-computed long-term financial market simulation data with ChatGPT integration capabilities.

## 🎯 Overview

This API provides access to a curated library of 40-year financial market path simulations, engineered to meet specific statistical targets. The system uses a hybrid approach combining numerical precision with semantic categorization for optimal ChatGPT integration.

### Key Features

- **🤖 ChatGPT Integration Ready**: Function definitions and semantic categorization
- **📊 Comprehensive Data**: 5,000+ pre-computed market simulation paths
- **🎭 Hybrid Approach**: Numerical data + semantic categories ("conservative", "aggressive")  
- **🐳 Dockerized**: Ready for production deployment
- **⚡ High Performance**: Stateless, cached data serving
- **📈 Rich Analytics**: Summary statistics, envelope charts, path details

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   ChatGPT API   │───▶│   FastAPI App    │───▶│  Pre-computed Data  │
│                 │    │                  │    │                     │
│ - Function Calls│    │ - /scenarios     │    │ - 5,000+ paths      │
│ - Semantic Terms│    │ - /paths         │    │ - Statistics        │
│ - Conversations │    │ - Categorization │    │ - Parameter Maps    │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

## 📁 Project Structure

```
Short_Term_Long_Term_Model_Project/
├── main.py                     # FastAPI application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Multi-container setup
├── chatgpt_functions.json      # ChatGPT function definitions
├── README.md                   # This file
└── Long Term Model/
    └── Long Term Model/
        ├── final_path_statistics_library.csv  # Main data file
        ├── param_library.csv                  # Parameter mappings
        └── *.py                               # Original model files
```

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone and navigate to project
cd Short_Term_Long_Term_Model_Project

# Build and run with Docker Compose
docker-compose up --build

# API will be available at http://localhost:8000
```

### Option 2: Direct Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn main:app --host 0.0.0.0 --port 8000

# Access at http://localhost:8000
```

## 📚 API Endpoints

### 🎯 Core Endpoints

#### `GET /long_term/scenarios`
Lists all available scenarios with semantic categorization.

**Response Example:**
```json
[
  {
    "target_mean": 0.06,
    "target_spread": 1.5,
    "description": "Moderate Scenario (6.0% Target Return)",
    "semantic_category": "moderate",
    "total_paths": 450
  }
]
```

#### `GET /long_term/paths?mean=0.06&spread=1.5`  
Returns comprehensive scenario analysis including statistics, envelope data, and path details.

**Response Structure:**
```json
{
  "scenario_info": {...},
  "summary_statistics": {
    "average_annual_return": 0.061,
    "average_max_drawdown": 0.42,
    "return_category": "moderate",
    "risk_category": "moderate"
  },
  "envelope_chart_data": {
    "years": [5, 10, 15, 20, 25, 30, 35, 40],
    "p05_path": [...],
    "p50_path": [...], 
    "p95_path": [...]
  },
  "path_details_table": [...]
}
```

### 🏥 Utility Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation

### ⚡ Short-Term Endpoints

Short-term crisis model focused on drawdown/recovery windows and regime baselines.

- `GET /short_term/levels` — Lists default crisis levels and parameter metadata.
  - Returns an array of objects:
    - `param_set_id`, `category`, `level_rank`, `drawdown`, `t_down`, `t_up`,
      `envelope_asym`, `annual_vol`, `df_returns`, `tanh_scale`, `max_daily_return`, `min_crisis_len`.

- `GET /short_term/baseline` — Precomputed monthly table comparing normal vs fragile regimes.
  - Response rows: `month`, `mean_normal`, `p10_normal`, `p90_normal`, `mean_fragile`, `p10_fragile`, `p90_fragile`.

- `GET /short_term/demo_summary` — Generates an in-memory demo set of accepted crisis paths for a chosen level and returns smoothed stats plus a monthly table.
  - Query params:
    - `level` (int, 1–7, default 3)
    - `n_paths` (int, 10–200, default 50)
    - `random_state` (int, optional)
  - Response:
    - `param_set`: `param_set_id`, `category`, `level_rank`, `drawdown`, `t_down`, `t_up`, `envelope_asym`
    - `stats`: list of `{ t_day, mean, p10, p90 }`
    - `monthly_table`: list of `{ month, mean, p10, p90 }`

## 🔌 How Models Plug Into The System

This service exposes two model families through a unified FastAPI app. Both plug in via thin adapters that load data, apply semantic labeling, and serialize responses for ChatGPT/UI consumption.

- Long-Term Model:
  - Source: precomputed CSVs under `Long Term Model/Long Term Model/`
  - Loader: `load_data()` caches `final_path_statistics_library.csv` and `param_library.csv`
  - Endpoints:
    - `GET /long_term/scenarios`: Enumerates available `(target_mean, target_spread)` pairs with semantic risk labels.
    - `GET /long_term/paths`: Filters the library by scenario and returns summary stats, an envelope proxy, and a trimmed path table.
  - Semantics: `categorize_return`, `categorize_spread`, `categorize_drawdown` produce ChatGPT-friendly labels.
  - Data Flow: CSV → pandas DataFrame (cached) → filtered/aggregated → Pydantic models → JSON.

- Short-Term Model:
  - Source: generator utilities in `short_term_crisis_generator.py` and the precomputed baseline `normal_vs_fragile_table.csv`.
  - Loader: `load_short_term_baseline()` caches the baseline CSV.
  - Endpoints:
    - `GET /short_term/levels`: Exposes 7 canonical crisis parameter sets (level 1–7) with metadata.
    - `GET /short_term/baseline`: Returns monthly normal vs fragile baseline table from CSV.
    - `GET /short_term/demo_summary`: Generates a small, in-memory sample of accepted crisis paths for a requested level, then returns smoothed stats and a monthly table. No filesystem writes.
  - Data Flow:
    - Levels/Baseline: Pydantic models over CSV/param metadata → JSON.
    - Demo Summary: ParamSet → synthetic crisis windows → compute summaries (`compute_summaries`, `monthly_table`) → JSON.

- ChatGPT Integration:
  - Function metadata lives in `chatgpt_functions.json` (long-term + short-term entries).
  - Semantic fields in responses make outputs easy to narrate.

- Cross-cutting Concerns:
  - Caching via `lru_cache` for CSV loads and startup warmup via FastAPI lifespan.
  - Error handling turns missing files or invalid params into helpful HTTP errors.
  - Tests verify endpoint shape and core logic for both models.

## 🤖 ChatGPT Integration

### Function Definitions

The API includes ChatGPT function definitions in `chatgpt_functions.json`:

```json
{
  "functions": [
    {
      "name": "get_longterm_scenarios",
      "description": "Get available investment scenarios...",
      "endpoint": "GET /long_term/scenarios"
    },
    {
      "name": "analyze_longterm_scenario", 
      "description": "Analyze specific investment scenario...",
      "endpoint": "GET /long_term/paths"
    }
  ]
}
```

### Semantic Categories

The API uses semantic terms that ChatGPT understands:

- **Risk Levels**: `conservative`, `moderate`, `aggressive`
- **Returns**: `very_low`, `low`, `moderate`, `high`, `very_high`  
- **Drawdowns**: `low`, `moderate`, `high`, `very_high`

### Usage Examples

```
User: "Show me conservative long-term investment options"
→ ChatGPT calls get_longterm_scenarios()
→ Filters for scenarios with semantic_category="conservative"

User: "What would a 6% moderate risk investment look like over 40 years?"  
→ ChatGPT calls analyze_longterm_scenario(mean=0.06, spread=2.0)
→ Returns complete analysis with charts and statistics
```

## 📊 Data Schema

### Main Data File: `final_path_statistics_library.csv`

| Column | Type | Description |
|--------|------|-------------|
| `path_id` | int | Unique path identifier |
| `target_mean` | float | Target annual return (e.g., 0.06) |
| `target_spread` | float | Target risk/volatility level |
| `actual_annual_return` | float | Achieved annual return |
| `max_drop` | float | Maximum drawdown experienced |
| `lost_decades` | int | Number of 10-year periods with negative returns |

### Parameter File: `param_library.csv`

| Column | Type | Description |
|--------|------|-------------|
| `target_mean` | float | Target annual return |
| `target_spread` | float | Target spread level |
| `opt_mu` | float | Optimized mu parameter |
| `opt_sigma` | float | Optimized sigma parameter |
| `opt_kappa` | float | Optimized kappa parameter |

## 🔧 Configuration

### Environment Variables

```bash
ENV=production              # Environment mode
LOG_LEVEL=info             # Logging level
PORT=8000                  # Server port (optional)
```

### Docker Configuration

The application includes:
- Multi-stage Docker build for optimization
- Non-root user for security
- Health checks for monitoring
- Volume mounting for data files

## 🛠️ Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest pytest-asyncio httpx

# Run tests (when implemented)
pytest tests/
```

### API Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 📈 Performance Features

- **Caching**: LRU cache for data loading
- **Pagination**: Limited path details for large datasets  
- **Compression**: Efficient data serialization
- **Stateless**: No session dependencies for horizontal scaling

## 🔒 Security Features

- **CORS Configuration**: Configurable cross-origin requests
- **Input Validation**: Pydantic models with constraints
- **Error Handling**: Structured error responses
- **Container Security**: Non-root user, minimal base image

## 🚀 Deployment

### Production Deployment

1. **Docker Hub Push**:
```bash
docker build -t your-registry/longterm-api:v1.0.0 .
docker push your-registry/longterm-api:v1.0.0
```

2. **Kubernetes Deployment**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: longterm-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: longterm-api
  template:
    metadata:
      labels:
        app: longterm-api
    spec:
      containers:
      - name: api
        image: your-registry/longterm-api:v1.0.0
        ports:
        - containerPort: 8000
```

### Integration with Main Application

To integrate with the main ChatGPT-powered application:

1. **Register Functions**: Add function definitions from `chatgpt_functions.json`
2. **Route Calls**: Configure routing engine to call this API
3. **Handle Responses**: Map API responses to UI components (tables/charts)

## 📞 Support & Maintenance

### Monitoring

- Health check endpoint: `/health`
- Structured logging throughout application
- Docker health checks configured

### Troubleshooting

**Common Issues:**

1. **Data files not found**: Ensure CSV files are in correct directory structure
2. **Permission errors**: Check file permissions and Docker user setup
3. **Memory issues**: Monitor data loading and consider pagination

### Extending the API

To add new endpoints:

1. Define Pydantic models in `main.py`
2. Add endpoint function with proper documentation
3. Update ChatGPT function definitions
4. Add tests for new functionality

## 📄 License

Professional implementation for client project.

## 👥 Contributing

This is a client-specific implementation. For modifications:

1. Follow existing code patterns
2. Maintain ChatGPT compatibility
3. Update documentation
4. Test thoroughly before deployment

---

**Built with ❤️ using FastAPI, designed for seamless ChatGPT integration**
