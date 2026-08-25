# 🤖 LLM Autonomous Trading Agent

> An AI-driven trading system that reads market data, news sentiment, and options chains — then makes paper-trading decisions with full explainable AI reasoning and audit trails.

![Python](https://img.shields.io/badge/Python-3.11+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange)

---

## 📌 Overview

This project builds an **autonomous trading agent** powered by Large Language Models (LLMs) that:

1. **Ingests** real-time market data (stocks, options chains, ETFs) via free APIs (yfinance, Alpha Vantage)
2. **Analyzes** news sentiment and macro events via NLP/LLM reasoning
3. **Decides** buy/sell/hold actions with a transparent, auditable reasoning chain
4. **Paper-trades** through a simulated brokerage with realistic slippage, commissions, and portfolio tracking
5. **Explains** every decision in plain English — full audit trail for each trade

The goal is **not** to beat the market (that's hard), but to demonstrate:
- End-to-end ML/LLM pipeline engineering
- Agentic decision-making with guardrails
- Explainable AI in a high-stakes domain
- Real-time data ingestion, processing, and visualization
- Robust software engineering (testing, CI/CD, monitoring)

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        TRADING AGENT LOOP                        │
│                                                                  │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐      │
│  │  Market   │   │   News   │   │ Options  │   │ Macro /  │      │
│  │  Data     │   │ Sentiment│   │  Chain   │   │ Econ     │      │
│  │  Feed    │   │  Engine  │   │  Feed    │   │  Feed     │      │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘      │
│       │              │              │              │              │
│       ▼              ▼              ▼              ▼              │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              FEATURE ENGINEERING LAYER               │        │
│  │  Technicals │ Sentiment Scores │ Greeks │ Vol Surface │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │                                         │
│                         ▼                                         │
│  ┌─────────────────────────────────────────────────────┐        │
│  │                  LLM REASONING ENGINE                 │        │
│  │                                                        │        │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐           │        │
│  │  │ Market  │  │  Risk    │  │ Portfolio │           │        │
│  │  │ Analyst │→│ Manager  │→│ Optimizer │           │        │
│  │  │ Agent   │  │ Agent    │  │ Agent     │           │        │
│  │  └─────────┘  └──────────┘  └──────────┘           │        │
│  │                        │                             │        │
│  │                        ▼                             │        │
│  │              ┌────────────────┐                     │        │
│  │              │  Decision +     │                     │        │
│  │              │  Rationale Text │                     │        │
│  │              └────────────────┘                     │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │                                         │
│                         ▼                                         │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              PAPER TRADING EXECUTOR                   │        │
│  │  Order Routing │ Slippage Sim │ Commission Sim       │        │
│  └──────────────────────┬──────────────────────────────┘        │
│                         │                                         │
│                         ▼                                         │
│  ┌─────────────────────────────────────────────────────┐        │
│  │              AUDIT TRAIL & DASHBOARD                  │        │
│  │  Trade Log │ Reasoning Log │ P&L Tracking │ Web UI   │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Multi-Agent Design

The system uses a **multi-agent architecture** where specialized LLM agents collaborate:

| Agent | Role | Inputs | Outputs |
|-------|------|--------|---------|
| **Market Analyst** | Technical analysis — trends, RSI, MACD, support/resistance | OHLCV data, technical indicators | Bullish/bearish/neutral signal + confidence |
| **Sentiment Analyst** | News & social sentiment aggregation | Headlines, financial news, earnings calls | Sentiment score per ticker |
| **Options Strategist** | Options chain analysis — IV percentile, Greeks, unusual activity | Options chains, IV, volume | Options trade recommendations |
| **Risk Manager** | Portfolio risk assessment — position sizing, exposure limits | Current portfolio, volatility, correlation | Max position size, risk flags |
| **Portfolio Optimizer** | Final decision synthesis — weighs all agent outputs | All agent outputs + risk constraints | Final trade decision + allocation |
| **Audit Logger** | Records every decision with full reasoning chain | All agent messages + final decision | Structured audit log entry |

### Decision Flow

```
MarketData → MarketAnalyst ──┐
NewsFeed   → SentimentAnalyst ──┤
OptionsChain → OptionsStrategist ──┤→ PortfolioOptimizer → [BUY/SELL/HOLD + rationale]
CurrentPortfolio → RiskManager ───┘         │
                                    ▼
                             AuditLogger → TradeExecutor → PaperBroker
```

---

## 📊 Data Sources (All Free)

| Source | Data | API |
|--------|------|-----|
| **yfinance** | Stock prices, historical OHLCV, options chains | Free, no key |
| **Alpha Vantage** | Technical indicators, extended fundamentals | Free tier (25 req/day) |
| **Finnhub** | Company news, earnings, insider sentiment | Free tier (60 req/min) |
| **FRED** | Macro economic data (rates, GDP, CPI) | Free, API key |
| **NewsAPI** / **GDELT** | Financial news headlines for sentiment | Free tier available |

---

## 🛠️ Tech Stack

### Core
- **Python 3.11+** — Main language
- **Pydantic** — Data validation & structured LLM outputs
- **LangChain** — Agent orchestration & prompt management
- **OpenAI API / local LLM** — Reasoning engine (GPT-4, Claude, or local Ollama)

### Data & ML
- **yfinance** — Market data ingestion
- **pandas / numpy** — Data manipulation
- **TA-Lib / pandas-ta** — Technical indicators
- **scikit-learn** — Lightweight ML models (sentiment, regression)
- **VADER / FinBERT** — Sentiment analysis

### Infrastructure
- **FastAPI** — REST API for control & monitoring
- **PostgreSQL** — Trade history, audit logs, portfolio state
- **Redis** — Real-time data caching & rate limiting
- **Celery** — Async task queue for scheduled runs
- **Docker** — Containerization
- **Docker Compose** — Local dev orchestration

### Frontend / Visualization
- **React + TypeScript** — Dashboard UI
- **TradingView Lightweight Charts** — Candlestick + indicator charts
- **Plotly / Dash** — Alternative Python-native dashboard

### DevOps
- **GitHub Actions** — CI/CD pipeline
- **pytest** — Testing
- **ruff + mypy** — Linting & type checking
- **pre-commit** — Git hooks

---

## 📁 Project Structure

```
llm-autonomous-trading-agent/
├── README.md
├── LICENSE
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── .github/
│   └── workflows/
│       ├── ci.yml                 # Lint, type-check, test
│       └── nightly-backtest.yml   # Run backtests on schedule
│
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py            # Pydantic settings (env-driven)
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── market_data.py         # yfinance wrapper — OHLCV, options
│   │   ├── news_feed.py           # News ingestion (Finnhub, GDELT)
│   │   ├── macro_feed.py          # FRED economic data
│   │   └── cache.py               # Redis caching layer
│   │
│   ├── features/
│   │   ├── __init__.py
│   │   ├── technicals.py          # RSI, MACD, Bollinger, ATR, etc.
│   │   ├── sentiment.py           # FinBERT / VADER sentiment scoring
│   │   ├── options_analysis.py    # IV percentile, Greeks, unusual activity
│   │   └── feature_store.py       # Unified feature vector assembly
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py          # Abstract agent interface
│   │   ├── market_analyst.py      # Technical analysis agent
│   │   ├── sentiment_analyst.py   # News sentiment agent
│   │   ├── options_strategist.py  # Options chain analysis agent
│   │   ├── risk_manager.py        # Portfolio risk agent
│   │   ├── portfolio_optimizer.py # Decision synthesis agent
│   │   └── audit_logger.py        # Audit trail recorder
│   │
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── paper_broker.py        # Simulated broker (slippage, commission)
│   │   ├── portfolio.py           # Portfolio state management
│   │   └── order.py               # Order types (market, limit, stop)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI app
│   │   ├── routes/
│   │   │   ├── portfolio.py       # GET /portfolio, GET /positions
│   │   │   ├── trades.py          # GET /trades, POST /trade
│   │   │   ├── agent.py           # GET /agent/status, POST /agent/run
│   │   │   └── audit.py           # GET /audit/{trade_id}
│   │   └── websocket.py          # Real-time updates via WebSocket
│   │
│   └── db/
│       ├── __init__.py
│       ├── models.py              # SQLAlchemy models
│       ├── session.py            # DB session factory
│       └── migrations/           # Alembic migrations
│
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── PortfolioView.tsx
│   │   │   ├── TradeHistory.tsx
│   │   │   ├── AuditTrail.tsx     # Decision reasoning explorer
│   │   │   └── AgentStatus.tsx
│   │   └── api/
│   │       └── client.ts
│   └── ...
│
├── tests/
│   ├── __init__.py
│   ├── test_market_data.py
│   ├── test_agents.py
│   ├── test_paper_broker.py
│   ├── test_portfolio.py
│   └── conftest.py
│
├── scripts/
│   ├── run_agent.py              # One-shot agent run
│   ├── backtest.py              # Historical backtesting harness
│   └── seed_data.py             # Download historical data for backtesting
│
└── notebooks/
    ├── 01_market_data_exploration.ipynb
    ├── 02_sentiment_analysis.ipynb
    ├── 03_options_strategy.ipynb
    └── 04_backtesting_results.ipynb
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Docker & Docker Compose
- (Optional) OpenAI API key or local LLM (Ollama)

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/llm-autonomous-trading-agent.git
cd llm-autonomous-trading-agent
cp .env.example .env  # Fill in your API keys
pip install -e ".[dev]"
```

### 2. Start Infrastructure

```bash
docker compose up -d  # PostgreSQL + Redis
alembic upgrade head  # Run DB migrations
```

### 3. Run the Agent (One-Shot)

```bash
python scripts/run_agent.py --tickers AAPL,MSFT,SPY --paper
```

### 4. Start the Dashboard

```bash
# Backend
uvicorn src.api.main:app --reload

# Frontend
cd frontend && npm install && npm run dev
```

Open `http://localhost:5173` to see the dashboard.

---

## 🔬 Backtesting

Run the agent against historical data to evaluate performance:

```bash
python scripts/backtest.py \
  --start 2024-01-01 \
  --end 2025-12-31 \
  --tickers AAPL,MSFT,NVDA,SPY \
  --initial-capital 100000 \
  --report output/backtest_report.html
```

### Backtest Metrics

- **Total Return** vs S&P 500 buy-and-hold
- **Sharpe Ratio** — Risk-adjusted returns
- **Max Drawdown** — Worst peak-to-trough decline
- **Win Rate** — % of profitable trades
- **Average Win / Average Loss** — Profit factor
- **Trade Frequency** — How often the agent trades
- **Reasoning Quality Score** — LLM-graded coherence of decisions

---

## 📝 Example Agent Decision (Audit Trail)

```json
{
  "timestamp": "2025-08-25T14:30:00Z",
  "ticker": "AAPL",
  "decision": "BUY",
  "action": {
    "type": "MARKET_BUY",
    "quantity": 50,
    "ticker": "AAPL",
    "estimated_price": 178.50
  },
  "confidence": 0.78,
  "reasoning": {
    "market_analyst": {
      "signal": "BULLISH",
      "confidence": 0.82,
      "rationale": "AAPL is trading above its 50-day and 200-day MA. RSI at 58 (not overbought). MACD histogram expanding positively. Broke out of 2-week consolidation on above-average volume."
    },
    "sentiment_analyst": {
      "signal": "BULLISH",
      "confidence": 0.71,
      "rationale": "12 positive vs 3 negative headlines in last 24h. Key catalyst: new product announcement at yesterday's event. Social sentiment on X/Twitter trending positive."
    },
    "options_strategist": {
      "signal": "NEUTRAL_BULLISH",
      "confidence": 0.65,
      "rationale": "IV percentile at 35th (below median — options are relatively cheap). Put/call ratio 0.85 (slightly bullish). No unusual sweep activity detected."
    },
    "risk_manager": {
      "signal": "APPROVE",
      "max_position": 75,
      "rationale": "Current portfolio has 12% cash available. AAPL beta is 1.2. Adding 50 shares at $178.50 = $8,925 = 8.9% of portfolio. Within single-position 15% limit. Portfolio correlation with AAPL already at 0.3 — acceptable."
    },
    "portfolio_optimizer": {
      "decision": "BUY 50 shares AAPL",
      "rationale": "Three of four agents bullish with consensus confidence 0.78. Risk manager approves position size. Sentiment catalyst (product launch) provides short-term tailwind. Executing market buy for immediate fill."
    }
  },
  "execution": {
    "fill_price": 178.52,
    "slippage": 0.02,
    "commission": 0.50,
    "fill_time": "2025-08-25T14:30:01Z"
  }
}
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Run specific module
pytest tests/test_agents.py -v
```

---

## 🐳 Docker

```bash
# Build and run everything
docker compose up --build

# Just the backend API
docker compose up api redis postgres

# Run tests in container
docker compose run --rm api pytest
```

---

## 🗺️ Roadmap

### Phase 1 — MVP (Weeks 1-3)
- [x] Market data ingestion (yfinance)
- [x] Basic technical indicators
- [x] Single-agent reasoning (Market Analyst)
- [x] Paper trading executor
- [x] CLI interface (`scripts/run_agent.py`)

### Phase 2 — Multi-Agent (Weeks 4-6)
- [ ] Sentiment analysis agent
- [ ] Options strategist agent
- [ ] Risk manager agent
- [ ] Multi-agent orchestration with LangChain
- [ ] Structured outputs (Pydantic)

### Phase 3 — Infrastructure (Weeks 7-9)
- [ ] PostgreSQL persistence layer
- [ ] Redis caching
- [ ] FastAPI REST API
- [ ] WebSocket real-time updates
- [ ] Scheduled runs via Celery

### Phase 4 — Dashboard (Weeks 10-12)
- [ ] React frontend
- [ ] Portfolio visualization
- [ ] Audit trail explorer (click any trade → see full reasoning)
- [ ] Backtesting UI

### Phase 5 — Polish (Weeks 13-15)
- [ ] Backtesting harness with metrics
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Documentation & blog post
- [ ] Deploy to cloud (Railway / Fly.io)
- [ ] Add LLM model selection (OpenAI / Anthropic / local)

### Future Ideas
- [ ] Live trading via Alpaca Markets API
- [ ] Reinforcement learning fine-tuning on backtest results
- [ ] Multi-portfolio support (different risk profiles)
- [ ] Options strategies (iron condors, credit spreads)
- [ ] Real-time Twitter/X sentiment streaming
- [ ] Mobile app for push notifications

---

## ⚠️ Disclaimer

This project is for **educational and research purposes only**. It uses **paper trading** (simulated money). No real money is at risk. Past performance does not guarantee future results. This is not financial advice.

---

## 📄 License

MIT — See [LICENSE](LICENSE)

---

## 🤝 Contributing

Pull requests welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 🔗 Links

- **Documentation:** [docs/](docs/) (WIP)
- **Live Demo:** Coming soon
- **Blog Post:** Coming soon
- **Author:** [Your Name](https://github.com/yourusername)
