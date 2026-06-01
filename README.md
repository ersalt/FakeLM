# 🤖 FakeLM

[中文文档](README_CN.md)

**FakeLM** is a satirical LLM API server that doesn't do any real neural-network inference.  
It generates plausible-looking text using random characters, Markov chains, and keyword-triggered templates — fully compatible with the **OpenAI Chat Completions API**.

> *Why run a 400B-parameter model when a few megabytes of Markov chain can produce the same amount of nonsense at 100x the speed?*

## 🎯 What is this for?

- Showcasing "fake intelligence" performance numbers (millions of tokens/s on a toaster)
- Testing OpenAI-compatible API clients (Lobe Chat, NextChat, Open WebUI, etc.) without needing a real model
- Having fun and/or trolling your colleagues

## ✨ Highlights

| Feature | Description |
|---------|-------------|
| ⚡ **Blazing speed** | No GPU required. 10 000+ tok/s on a potato CPU. |
| 🔌 **OpenAI compatible** | Drop-in replacement for `/v1/chat/completions` (streaming & non-streaming) and `/v1/models` |
| 🎭 **Trolling modes** | Fake rate-limit errors (HTTP 429), random 500s, configurable thinking delay |
| 🧩 **Plugable generators** | Random character, Markov chain (character-level n-gram), keyword templates, composite strategy |
| 🌐 **Built-in Web UI** | ChatGPT-style chat interface served from `/static/index.html` |
| ⚙️ **Config-driven** | Switch generators, tune parameters, and load custom data via `data/config.yaml` |
| 🌍 **Bilingual** | Chinese + English keyword groups with per-language auto-extend |

## 🚀 Quick Start

### Requirements

- Python **3.10+**
- pip

### 1. Clone & install

```bash
git clone https://github.com/ersalt/FakeLM.git
cd FakeLM
pip install -r fakellm/requirements.txt
```

### 2. Run

```bash
python main.py
```

The server starts at `http://localhost:8000`.  
Open `http://localhost:8000/static/index.html` in your browser for the built-in chat UI.

### 3. (Optional) Use with any OpenAI-compatible client

Point your API client's base URL to `http://localhost:8000/v1`. No API key required.

```bash
# Quick test with curl (non-streaming)
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"fake-gpt-4","messages":[{"role":"user","content":"Hello!"}]}'

# Streaming
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"fake-gpt-4","messages":[{"role":"user","content":"Tell me a story."}],"stream":true}'
```

## 🐳 Docker

```bash
docker build -t fakellm .
docker run -p 8000:8000 fakellm
```

## ⚙️ Configuration

Edit `fakellm/data/config.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8000

generation:
  default_engine: "composite"
  # Available engines: random_char, markov, template, composite

logging:
  level: "INFO"
```

### Generator engines

| Engine | Description |
|--------|-------------|
| `random_char` | Pure random characters from a mixed CJK+ASCII set. Fastest. |
| `markov` | Character-level n-gram Markov chain (default 2-gram Chinese). |
| `template` | Keyword-regex matching against `data/topics/topics.json`. Falls back to random when no match. |
| `composite` | Routes to one of the above based on `intelligence` parameter (0.0 → random, 0.5 → template, 1.0 → markov). |

### Topics / templates

Edit `fakellm/data/topics/topics.json` to add your own keyword → reply mappings.  
Both Chinese and English keyword groups are supported; the generator auto-detects language for sentence extension.

## 📁 Project Structure

```
fakellm/
├── server/app.py              # FastAPI application & routes
├── api_adapters/openai.py     # OpenAI ←→ Internal request conversion
├── generation/
│   ├── base.py                # BaseGenerator abstract class
│   ├── random_char.py         # Random character generator
│   ├── markov.py              # Markov chain generator
│   ├── template.py            # Keyword-template generator
│   └── composite.py           # Composite routing generator
├── data/
│   ├── config.yaml            # Main configuration
│   ├── topics/topics.json     # Keyword → replies mapping
│   └── markov_chains/         # n-gram transition matrices
├── utils/
│   └── randomness.py          # Seeded RNG utility
├── config.py                  # pydantic-settings config loader
└── requirements.txt
static/                        # Front-end (ChatGPT-style UI)
tests/                         # pytest test suite
main.py                        # Entry point
```

## 🧪 Running Tests

```bash
pytest tests/ -v
```

## 🎭 Stats & Performance Info

Every completion response (streaming & non-streaming) includes generation stats:

- **Streaming**: an SSE `x_fakellm_stats` event with `engine`, `elapsed` seconds, `tokens` count, and `speed` (tok/s)
- **Non-streaming**: `elapsed` and `tokens_generated` fields in the response JSON
- The Web UI renders these stats as a small grey footer below each assistant message

## 📜 License

MIT — see [LICENSE](LICENSE).

## 🙃 Disclaimer

This is a joke project. It does **not** contain any real AI or machine learning model.  
Any resemblance to actual intelligence is purely coincidental (and probably accidental overfitting of a 2-gram table).