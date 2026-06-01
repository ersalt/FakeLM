# FakeLM - Architecture & Design Specification

## 1. 核心数据流
```
Client (OpenAI SDK) → FastAPI (OpenAI adapter) → InternalRequest → Generator → token stream → OpenAI response format → Client
```
- 请求进入 `/v1/chat/completions`，`openai.py` 解析 JSON 为 `InternalRequest`。
- 根据 `config.yaml` 选择生成器实例，调用 `generate()` 获得 token 迭代器。
- 若 `stream=True`，将迭代器包装为 SSE 响应；否则收集所有 token 后返回 JSON。

## 2. 内部数据模型 (`api_adapters/base.py`)

```python
from pydantic import BaseModel
from typing import Optional, Dict, Any

class InternalRequest(BaseModel):
    prompt: str                     # 用户最后一条消息内容（或拼接对话历史）
    temperature: float = 1.0        # 0.0~2.0，影响随机性
    max_tokens: int = 100
    stream: bool = False
    # 可选扩展字段
    intelligence: float = 0.5       # 0=纯随机, 1=最高“智能”（依赖马尔可夫/模板）
    seed: Optional[int] = None      # 随机种子，用于可复现性
    extra: Dict[str, Any] = {}      # 存放厂商特定参数

class InternalResponse(BaseModel):
    text: str
    tokens_used: int
    finish_reason: str = "stop"
```

## 3. 生成器抽象接口 (`generation/base.py`)

```python
from abc import ABC, abstractmethod
from typing import Iterator, Optional
from fakellm.api_adapters.base import InternalRequest

class BaseGenerator(ABC):
    """所有生成器必须实现此接口"""
    
    @abstractmethod
    def generate(self, request: InternalRequest) -> Iterator[str]:
        """
        返回一个迭代器，每次产出一个 token（可以是单个字符或单词）。
        支持非流式调用（直接 list(iterator)）和流式输出。
        """
        pass
    
    @abstractmethod
    def get_metadata(self) -> dict:
        """返回生成器信息，用于 /v1/models 或日志"""
        pass
```

## 4. 各生成器实现细节

### 4.1 纯随机字符 (`RandomCharGenerator`)
- 从预定义字符集中均匀采样：`ascii_letters + digits + 常用标点 + 部分汉字（范围 0x4E00-0x9FFF）`。
- 每个 token 为一个字符。
- 参数 `temperature` 无用，但可保留。
- 速度最快，无状态。

### 4.2 马尔可夫链生成器 (`MarkovGenerator`)
- 支持 1-gram、2-gram、3-gram（可通过配置 `n` 指定）。
- 转移矩阵存储格式：JSON 字典，键为 `prefix`（字符串或元组），值为 `list` 可能的后继字符/词。
- 为简化，采用**字符级别** n-gram（适合中文和英文混合）。
- 启动时从 `data/markov_chains/{name}.json` 加载矩阵。
- 采样时根据当前 n-1 个字符查找后继；若无后继，回退到低阶或随机字符。
- 支持设置 `temperature` 对概率分布进行缩放（若矩阵存储的是概率，则可调整；若存储频次，则使用频次采样）。

### 4.3 模板匹配生成器 (`TemplateGenerator`)
- 从 `data/topics/topics.json` 加载映射：`{"keyword_pattern": ["reply1", "reply2"]}`。
- `keyword_pattern` 为正则表达式字符串（如 `"你好|hello"`）。
- 生成时扫描 `InternalRequest.prompt`，匹配第一个命中的关键字，随机选择一条回复。
- 若无匹配，返回默认回复（可配置）。
- 回复中可包含占位符 `{random_num}` 等，简单替换。

### 4.4 组合生成器 (`CompositeGenerator`)
- 根据 `InternalRequest.intelligence` 值选择子生成器：
  - `intelligence <= low_threshold` → 用 `RandomCharGenerator`
  - `intelligence >= high_threshold` → 用 `MarkovGenerator`
  - 中间区域 → 用 `TemplateGenerator`
- 阈值在配置文件中定义。
- 也可按比例混合输出（如每 10 个 token 切换一次），但初版简单路由即可。

## 5. API 适配器

### 5.1 OpenAI 适配器 (`api_adapters/openai.py`)
- 实现两个端点：
  - `POST /v1/chat/completions`：解析 OpenAI 请求格式。
  - `GET /v1/models`：返回虚假模型列表。
- 请求转换规则：
  - 从 `messages` 数组中取最后一条 `role="user"` 的 `content` 作为 `prompt`。
  - 将 `temperature`、`max_tokens`、`stream` 直接映射。
  - 扩展字段：若请求中有 `intelligence_level` 或 `fake_intelligence`，存入 `extra`。
- 响应格式：
  - 非流式：标准 OpenAI ChatCompletion 对象，`choices[0].message.content` 填充生成的文本。
  - 流式：每个 chunk 包含 `delta.content`，最后一个 chunk 的 `finish_reason="stop"`。

## 6. 配置系统

- 使用 `pydantic_settings` 读取 YAML 文件。
- 配置文件示例 `data/config.yaml`：

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  cors_origins: ["*"]
  fake_rate_limit: 0        # 0 为不启用，>0 表示每请求随机返回 429 的概率

generation:
  default_engine: "composite"
  engines:
    random_char:
      charset: "ascii+digit+common_chinese"
    markov:
      n: 2
      chain_file: "data/markov_chains/zh_2gram.json"
      fallback_to_random: true
    template:
      topics_file: "data/topics/topics.json"
      default_reply: "我是一个随机模型，请提出更明确的问题。"
    composite:
      low_threshold: 0.3
      high_threshold: 0.7
      low_engine: "random_char"
      mid_engine: "template"
      high_engine: "markov"

logging:
  level: "INFO"
  show_tokens_per_second: true
```

- 主程序启动时加载配置，初始化生成器实例。

## 7. 流式输出机制

- 使用 FastAPI 的 `StreamingResponse`，媒体类型 `text/event-stream`。
- 每个 chunk 格式：`data: {"id":"...","choices":[{"delta":{"content":"字"}}]}\n\n`
- 生成器 `generate()` 返回同步迭代器，在异步端点中调用需使用 `async for` 或 `iter` 配合 `next()`。为简化，将同步迭代器包裹在异步生成器内：

```python
async def stream_wrapper(iterator):
    for chunk in iterator:
        yield f"data: {json.dumps(chunk)}\n\n"
        await asyncio.sleep(0)  # 让出控制权
    yield "data: [DONE]\n\n"
```

## 8. 扩展点指南

- **新增生成器**：继承 `BaseGenerator`，实现 `generate` 和 `get_metadata`，然后在 `config.yaml` 的 `engines` 下添加配置，并在 `generation/__init__.py` 中注册。
- **新增 API 兼容层**：新建模块 `api_adapters/anthropic.py`，内部实现请求解析和响应封装，并在 `server/app.py` 中挂载路由。
- **替换随机数后端**：修改 `utils/randomness.py`，统一使用 `random.Random(seed)` 实例，便于注入种子。

## 9. 性能与错误模拟（整活）

- 在中间件中实现随机延迟（如 `random.uniform(0.05, 0.2)` 秒），模拟推理时间。
- 随机返回 HTTP 429（Too Many Requests）或 500（Internal Error），概率由配置控制。
- 在响应头中添加 `X-FakeLM-Speed: 234567 tokens/s` 虚假性能信息。