# FakeLM - Project Overview

## 项目目标
FakeLM 是一个 **模拟大模型 API 的“整活”服务器**，它不执行任何真实的神经网络推理，而是通过随机生成、马尔可夫链、模板匹配等方式产生看起来“像模像样”的文本输出。它完全兼容 OpenAI Chat Completions API，可被任何支持该 API 的客户端（如 Lobe Chat, NextChat, Open WebUI）调用，以极高的 token 吞吐量展示“虚假智能”。

## 核心特性
- 🚀 **极高速度**：由于没有真实推理，在普通 CPU 上即可达到数万 tokens/s，在 GPU 上可达数百万 tokens/s。
- 🧩 **可插拔生成器**：支持多种输出策略（纯随机字符、马尔可夫链、关键词模板、组合策略），可通过配置文件切换。
- 🔌 **OpenAI 兼容**：实现 `/v1/chat/completions`（流式与非流式）和 `/v1/models` 端点。
- 🎭 **整活功能**：模拟速率限制、随机错误、伪造 thinking 延迟、返回虚假的 token 用量。
- ⚙️ **配置驱动**：所有生成器参数、主题词库、马尔可夫转移矩阵均从外部文件加载，无需修改代码。

## 技术栈
- **语言**：Python 3.10+
- **Web 框架**：FastAPI + Uvicorn
- **数据校验**：Pydantic v2
- **配置管理**：PyYAML + pydantic-settings
- **随机数**：Python 内置 `random` 模块（支持种子）
- **流式输出**：Server-Sent Events (SSE) via `StreamingResponse`
- **测试**：pytest + httpx

## 设计原则
1. **接口与实现分离**：API 适配层（OpenAI 格式）与内部生成引擎完全解耦。
2. **生成器抽象**：所有生成器实现统一的 `BaseGenerator` 接口，可任意组合。
3. **异步优先**：Web 层使用异步，生成器支持同步或异步迭代器。
4. **配置驱动**：关键行为（如启用哪个生成器、马尔可夫阶数、模板路径）由 `config.yaml` 控制。
5. **易于扩展**：新增生成器或 API 兼容层只需添加一个类并注册。

## 目标用户
- 想体验“极速大模型”的开发者
- 需要测试 API 客户端行为的学生/工程师
- 整活爱好者、技术播主

## 非功能性要求
- 单机应能处理至少 1000 并发请求（纯随机生成器下）
- 启动时间 < 2 秒
- 内存占用 < 200MB（加载马尔可夫矩阵后 < 500MB）

## 目录结构（最终形态）
```
fakellm/
├── server/
│   ├── __init__.py
│   ├── app.py               # FastAPI 应用入口
│   └── middleware.py        # CORS、日志、伪造速率限制
├── api_adapters/
│   ├── __init__.py
│   ├── base.py              # 内部统一请求/响应模型
│   └── openai.py            # OpenAI 格式转换及路由
├── generation/
│   ├── __init__.py
│   ├── base.py              # BaseGenerator 抽象类
│   ├── random_char.py       # 纯随机字符生成器
│   ├── markov.py            # 马尔可夫链生成器
│   ├── template.py          # 基于关键词模板的生成器
│   └── composite.py         # 混合策略生成器
├── data/
│   ├── markov_chains/
│   │   └── zh_2gram.json    # 示例 2-gram 转移矩阵
│   ├── topics/
│   │   └── topics.json      # 关键词到回复列表的映射
│   └── config.yaml          # 主配置文件
├── utils/
│   ├── __init__.py
│   ├── randomness.py        # 带种子的随机数生成器
│   └── streaming.py         # 流式辅助函数（异步队列）
├── tests/
│   ├── test_api.py
│   ├── test_generators.py
│   └── conftest.py
└── requirements.txt
```

## 开发阶段
详见 `TASKS.md`