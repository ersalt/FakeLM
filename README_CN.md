# 🤖 FakeLM

[English](README.md)

**FakeLM** 是一个「整活」向的 LLM API 服务器，它**不执行任何真实的神经网络推理**。  
通过随机字符生成、马尔可夫链、关键词模板等方式产出「看起来像模像样」的文本，并**完全兼容 OpenAI Chat Completions API**。

> *跑什么 400B 参数大模型？几张马尔可夫转移表就能产出等量的废话，速度还快 100 倍。*

## 🎯 这玩意儿能干啥？

- 展示「虚假智能」的逆天性能数据（在烤面包机上跑出百万 tokens/s）
- 在没有真实模型的情况下，测试 OpenAI 兼容的 API 客户端（Lobe Chat、NextChat、Open WebUI 等）
- 整活、炫技、逗同事

## ✨ 亮点

| 特性 | 说明 |
|------|------|
| ⚡ **极速生成** | 纯 CPU 即可跑出 10 000+ tok/s，无需 GPU |
| 🔌 **OpenAI 兼容** | 可直接替代 `/v1/chat/completions`（支持流式/非流式）和 `/v1/models` |
| 🎭 **整活模式** | 伪造速率限制（HTTP 429）、随机 500 错误、假装在思考的延迟 |
| 🧩 **可插拔生成器** | 纯随机字符、马尔可夫链（字符级 n-gram）、关键词模板、混合策略 |
| 🌐 **内置 Web 界面** | ChatGPT 风格聊天 UI，访问 `/static/index.html` 即可使用 |
| ⚙️ **配置驱动** | 所有生成器参数、词库均通过 `data/config.yaml` 控制，无需改代码 |
| 🌍 **双语言支持** | 中英文关键词组分别处理，auto_extend 按语言自动选择标点策略 |

## 🚀 快速开始

### 环境要求

- Python **3.10+**
- pip

### 1. 克隆项目并安装依赖

```bash
git clone https://github.com/ersalt/FakeLM.git
cd FakeLM
pip install -r fakellm/requirements.txt
```

### 2. 启动服务

```bash
python main.py
```

服务运行在 `http://localhost:8000`。  
在浏览器中打开 `http://localhost:8000/static/index.html` 即可使用内置聊天界面。

### 3. （可选）对接 OpenAI 兼容客户端

将 API 客户端的 base URL 指向 `http://localhost:8000/v1`，无需 API Key。

```bash
# 命令行测试（非流式）
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"fake-gpt-4","messages":[{"role":"user","content":"你好！"}]}'

# 流式测试
curl -N http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"fake-gpt-4","messages":[{"role":"user","content":"讲个故事。"}],"stream":true}'
```

## 🐳 Docker 部署

```bash
docker build -t fakellm .
docker run -p 8000:8000 fakellm
```

## ⚙️ 配置说明

编辑 `fakellm/data/config.yaml`：

```yaml
server:
  host: "0.0.0.0"
  port: 8000

generation:
  default_engine: "composite"
  # 可选引擎: random_char, markov, template, composite

logging:
  level: "INFO"
```

### 生成器引擎一览

| 引擎 | 说明 |
|------|------|
| `random_char` | 纯随机字符，从 CJK + ASCII 混合字符集中均匀采样。速度最快。 |
| `markov` | 字符级 n-gram 马尔可夫链（默认为中文 2-gram）。 |
| `template` | 对用户输入进行关键词正则匹配，从 `data/topics/topics.json` 中随机选择回复。无匹配时回退到随机生成。 |
| `composite` | 根据请求中的 `intelligence` 参数路由到以上引擎之一（0.0 → 随机，0.5 → 模板，1.0 → 马尔可夫）。 |

### 主题词库 / 模板

编辑 `fakellm/data/topics/topics.json` 可以添加你自己的关键词 → 回复映射。  
文件内同时支持中英文关键词组，生成器会自动检测语言并使用对应的标点策略进行句子扩展。

## 📁 项目结构

```
fakellm/
├── server/app.py              # FastAPI 应用与路由
├── api_adapters/openai.py     # OpenAI 格式 ⇄ 内部请求转换
├── generation/
│   ├── base.py                # BaseGenerator 抽象基类
│   ├── random_char.py         # 随机字符生成器
│   ├── markov.py              # 马尔可夫链生成器
│   ├── template.py            # 关键词模板生成器
│   └── composite.py           # 混合路由生成器
├── data/
│   ├── config.yaml            # 主配置文件
│   ├── topics/topics.json     # 关键词 → 回复映射
│   └── markov_chains/         # n-gram 转移矩阵
├── utils/
│   └── randomness.py          # 带种子的随机数工具
├── config.py                  # pydantic-settings 配置加载
└── requirements.txt
static/                        # 前端（ChatGPT 风格界面）
tests/                         # pytest 测试套件
main.py                        # 入口点
```

## 🧪 运行测试

```bash
pytest tests/ -v
```

## 🎭 生成统计信息

每次补全响应（流式和非流式）都会附带生成统计：

- **流式**：SSE `x_fakellm_stats` 事件，包含 `engine`（引擎名）、`elapsed`（耗时秒）、`tokens`（token 数）和 `speed`（tok/s）
- **非流式**：响应 JSON 中包含 `elapsed` 和 `tokens_generated` 字段
- Web 前端会在每条 assistant 消息下方以灰色小字展示这些统计信息

## 📜 许可证

MIT — 详见 [LICENSE](LICENSE)。

## 🙃 免责声明

这是一个整活项目，**不包含任何真实的 AI 或机器学习模型**。  
任何与真实智能的相似之处纯属巧合（也许是你那个 2-gram 表过拟合了）。