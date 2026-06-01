# FakeLM - Development Tasks

本任务清单按优先级和依赖关系排序，建议 Cline 按阶段逐步实现。每个任务包含期望的文件路径和简短说明。

## 阶段 0：项目骨架与环境
- [ ] 创建项目目录结构（参考 `PROJECT_OVERVIEW.md` 中的树形图）。
- [ ] 编写 `requirements.txt`，包含：
  ```
  fastapi==0.104.1
  uvicorn[standard]==0.24.0
  pydantic==2.5.0
  pydantic-settings==2.1.0
  pyyaml==6.0.1
  httpx==0.25.1  # 用于测试
  pytest==7.4.3
  ```
- [ ] 创建 `data/config.yaml` 初始版本（内容参考 `ARCHITECTURE.md` 中的示例）。
- [ ] 创建 `data/topics/topics.json` 示例：
  ```json
  {
    "你好|您好|hi": ["你好！我是FakeLM，每秒可生成百万tokens。", "您好，请问需要随机什么？"],
    "天气": ["今天天气随机，50%概率晴天。", "我不关心天气，我只随机生成文本。"]
  }
  ```
- [ ] 创建 `data/markov_chains/zh_2gram.json` 占位文件（空对象 `{}`，后续可训练真实数据）。

## 阶段 1：核心基础模块
- [ ] `utils/randomness.py`：实现 `get_rng(seed: Optional[int] = None) -> random.Random` 函数。
- [ ] `generation/base.py`：定义 `BaseGenerator` 抽象类和 `InternalRequest`/`InternalResponse`（Pydantic 模型）。
- [ ] `generation/random_char.py`：实现 `RandomCharGenerator`：
  - 使用字符集：`string.digits + string.ascii_letters + string.punctuation + '的一是不了人我在有他这中大来上国个到说们为子和你地出也时年得就那要下'`
  - `generate()` 产生 `max_tokens` 个随机字符，每个字符单独 yield。
- [ ] `api_adapters/base.py`：导出 `InternalRequest`, `InternalResponse`（可从 `generation.base` 导入，但放在此处便于统一）。
- [ ] `api_adapters/openai.py`：
  - 实现 `def to_internal(request_dict: dict) -> InternalRequest`
  - 实现 `def from_internal(response: InternalResponse, stream: bool, model: str) -> dict`（用于非流式）
- [ ] `server/app.py`：
  - 创建 FastAPI app，添加 CORS 中间件。
  - 添加 `GET /v1/models`：返回固定模型列表 `["fake-gpt-4", "random-llm"]`。
  - 添加 `POST /v1/chat/completions` 路由（非流式），调用 `RandomCharGenerator` 生成回复。

**测试**：运行 `uvicorn server.app:app --reload`，使用 `curl` 测试非流式请求，确保返回有效 JSON。

## 阶段 2：生成器完善
- [ ] `generation/template.py`：实现 `TemplateGenerator`：
  - 加载 `data/topics/topics.json`。
  - 对每个请求，遍历关键词正则，匹配则随机选择回复并 yield 整个回复（可拆分为字符迭代器）。
- [ ] `generation/markov.py`：实现 `MarkovGenerator`：
  - 从 `data/markov_chains/zh_2gram.json` 加载矩阵（若文件为空则构建一个简单的回退模型）。
  - 实现 `_walk(prefix, max_steps, temperature)` 方法，逐字符 yield。
  - 支持前缀溢出处理。
- [ ] `generation/composite.py`：实现 `CompositeGenerator`：
  - 初始化时接收子生成器字典和阈值。
  - `generate` 根据 `intelligence` 选择相应子生成器代理调用。
- [ ] 修改 `server/app.py` 中的 `/v1/chat/completions` 路由：从配置选择默认生成器（可硬编码为 `composite` 进行测试）。

## 阶段 3：流式输出与配置集成
- [ ] 修改 `api_adapters/openai.py` 增加流式响应构建函数：
  - `def stream_response(generator, request: InternalRequest) -> StreamingResponse`
- [ ] 在 `server/app.py` 中处理 `stream=True` 分支，调用上述函数。
- [ ] 集成配置系统：
  - 创建 `config.py`，使用 `pydantic-settings` 加载 `data/config.yaml`。
  - 将配置对象传递给生成器工厂。
- [ ] 实现生成器工厂 `generation/__init__.py` 中的 `get_generator(config) -> BaseGenerator`。
- [ ] 测试流式输出（使用 `curl -N` 或 OpenAI Python SDK）。

## 阶段 4：整活特性与中间件
- [ ] `server/middleware.py`：
  - 随机延迟中间件：`random.uniform(0, 0.5)` 秒 sleep。
  - 随机错误中间件：按配置概率返回 `HTTPException(429)` 或 `500`。
- [ ] 添加 `X-FakeLM-Engine` 和 `X-FakeLM-Speed` 响应头（在生成器中计算每秒 token 数）。
- [ ] 日志记录：使用 `loguru` 记录每个请求的 prompt 摘要、生成 token 数、耗时和速度。

## 阶段 5：测试与文档
- [ ] 编写 `tests/test_generators.py`：测试每个生成器的基础功能（输出长度、字符范围）。
- [ ] 编写 `tests/test_api.py`：使用 `httpx.AsyncClient` 测试 `/v1/chat/completions` 端点的非流式和流式。
- [ ] 编写 `README.md`：整活风格的使用说明，包含 Docker 运行示例。
- [ ] 创建 `Dockerfile`：
  ```dockerfile
  FROM python:3.10-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install -r requirements.txt
  COPY . .
  CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8000"]
  ```

## 可选增强任务（后期）
- [ ] 支持更多 API 格式（Ollama、Anthropic）。
- [ ] 提供脚本从真实语料库训练马尔可夫矩阵。
- [ ] 简单的前端聊天界面（Streamlit 或 HTML+JS）。
- [ ] 性能压测脚本（使用 `locust` 或 `wrk`）。

---

**开发建议**：Cline 每次只关注一个任务，完成并测试后再进行下一个。遇到跨模块依赖时可先写 stub 或 mock。所有代码需包含类型注解和简短的 docstring。