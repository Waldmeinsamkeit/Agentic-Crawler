
---

# 🚀 AI Crawler Framework

**AI Crawler Framework** 是一个企业级的、具备自愈能力的自驱动爬虫 Agent 框架。它将浏览器自动化操作（Browser-use）与复杂的逻辑编排（LangGraph）相结合，并通过标准化的 **MCP (Model Context Protocol)** 协议对外提供情报能力。

本框架的核心设计哲学是：**手脚（浏览器）与大脑（逻辑编排）分离，通用抓取与专业分析（领域专家）解耦。**

---

## 🏗️ 项目架构 (Architecture)

框架采用分层解耦设计，确保高度的可扩展性：

Plaintext

```
my-agent-framework/
├── mcp_server.py           # MCP 协议入口，暴露 Tool/Resource 接口
├── config.py               # 基于 Pydantic-Settings 的全局配置管理
├── main.py                 # 本地独立运行入口（无需 MCP 客户端）
├── graph/                  # 核心编排层 (LangGraph)
│   ├── state.py            # 状态定义 (TypedDict/State)
│   ├── nodes/              # 逻辑节点 (调用各专家 Agent)
│   ├── edges.py            # 路由策略 (重试/结束/继续)
│   └── workflow.py         # 图组装 + Checkpointer 持久化集成
├── agents/                 # 执行专家层
│   ├── base.py             # Agent 抽象基类契约
│   ├── browser_executor.py # Browser-use 浏览器执行专家
│   └── intelligence/       # 领域分析专家 (科技/金融/竞品)
├── utils/                  # 基础设施层
│   ├── model_factory.py    # 多模型供应商 (LLM Provider) 抽象工厂
│   └── db_handler.py       # 业务数据库仓库 (SQLAlchemy)
└── checkpoints/            # 存放 LangGraph 状态快照的 SQLite 文件
```

---

## ✨ 核心特性 (Key Features)

- **🔄 鲁棒的状态机调度**：基于 LangGraph 的有向图架构，支持任务的**循环执行、错误回溯和断点续传**。
    
- **🔗 标准化 MCP 接口**：原生支持 MCP 协议，可作为工具无缝接入 Claude Desktop、Cursor 或 IDE。
    
- **🎭 领域专家 Agent 设计**：
    
    - **Browser Executor**: 专门负责复杂的网页交互与原始数据采集。
        
    - **Intelligence Analyst**: 针对特定领域（科技动态、金融财报）进行深度情报建模。
        
- **🤖 全模型支持 (Model Agnostic)**：通过 `ModelFactory` 统一调用 OpenAI, Anthropic, Google, Ollama, DeepSeek, Qwen 等模型。
    
- **💾 双重持久化策略**：
    
    - **Checkpointer DB**: 存储图的执行快照，支持通过 `thread_id` 恢复中断的任务。
        
    - **Business DB**: 存储最终的情报产物、结构化 JSON 和任务汇总报告。
        

---

## ⚡ 快速开始 (Quick Start)

### 1. 环境安装

Bash

```
pip install -r requirements.txt
playwright install
```

### 2. 准备环境配置

参考 `.env.example` 创建你的本地配置文件：

Bash

```
cp .env.example .env
```

在 `.env` 中配置你的 API Key 以及偏好的模型供应商（如 `BROWSER_PROVIDER=openai`）。

### 3. 运行本地独立任务

如果你只想在终端查看爬取效果：

Bash

```
python main.py
test_task = "Visit TechCrunch and find the 3 most important AI funding news recently."
#将task改成你要测试的内容

```

### 4. 启动 MCP 服务

若要将能力提供给 Claude 或其他 MCP 客户端：

Bash

```
python mcp_server.py
```

---

## 🛠️ 扩展性指南 (Extensibility)

### 增加新的情报分析专家

1. 在 `agents/intelligence/` 目录下新建分析类并继承 `BaseAgent`。
    
2. 在 `graph/nodes/` 中根据业务逻辑引入该专家。
    

### 增加新的模型供应商

在 `utils/model_factory.py` 中添加新的 Provider 映射，即可在全局 `config.py` 中一键切换。

---

## 📝 开发备注 (Notes)

- **断点恢复**：在调用任务时使用相同的 `thread_id` 即可从上一次失败或中断的状态（Checkpoint）继续运行。
    
- **人工介入 (HITL)**：若浏览器步骤因验证码或登录被拦截，状态将被标记并持久化，支持人工处理后继续。
    
- **配置优先级**：环境变量 > `.env` 文件 > 默认配置。
    

---

## 下一步计划 (Roadmap)

- [ ] 增加多并发浏览器上下文隔离。
    
- [ ] 集成向量数据库 (ChromaDB) 实现历史情报的 RAG 查询。
    
- [ ] 完善 MCP Resource 接口以支持图片/截图流式传输。
