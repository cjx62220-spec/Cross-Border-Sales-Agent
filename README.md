# Cross-Border Sales Agent

跨境私域智能获客与售前助理系统 — 基于 ReAct 模式的多工具 AI Agent，支持 RAG 知识库检索、线索自动捕获、后台审计与邮件通知。

<p align="center">
  <img src="https://img.shields.io/badge/Version-5.2.0-gold?style=for-the-badge" alt="Version">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Vue-3-4fc08d?style=for-the-badge&logo=vuedotjs&logoColor=white" alt="Vue3">
  <img src="https://img.shields.io/badge/WebSocket-Realtime-orange?style=for-the-badge" alt="WebSocket">
</p>

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend Layer                        │
│  ┌──────────────────┐    ┌────────────────────────────┐ │
│  │  Vue 3 SPA       │    │  Gradio Console            │ │
│  │  (index.html)    │    │  (app.py :7860)            │ │
│  │  WebSocket       │    │  HTTP Streaming            │ │
│  └────────┬─────────┘    └──────────┬─────────────────┘ │
│           │ ws://8000               │ import             │
├───────────┼─────────────────────────┼────────────────────┤
│           ▼                         ▼                    │
│  ┌─────────────────────────────────────────────────────┐ │
│  │              FastAPI Server (server.py)             │ │
│  │         WebSocket + REST API  :8000                 │ │
│  └─────────────────────┬───────────────────────────────┘ │
│                        ▼                                 │
│  ┌─────────────────────────────────────────────────────┐ │
│  │           Agent Core Engine (main.py)               │ │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  │ │
│  │  │ ReAct    │  │ RAG Pipeline │  │ Tool Router  │  │ │
│  │  │ Loop     │  │ (ChromaDB)   │  │              │  │ │
│  │  └──────────┘  └──────────────┘  └──────────────┘  │ │
│  └──────────┬──────────────┬──────────────┬────────────┘ │
│             ▼              ▼              ▼              │
│  ┌───────────────┐ ┌──────────────┐ ┌─────────────────┐ │
│  │ SQLite DB     │ │ ChromaDB     │ │ SMTP Email      │ │
│  │ (database.py) │ │ Vector Store │ │ (Async Notify)  │ │
│  └───────────────┘ └──────────────┘ └─────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 核心功能

- **ReAct 智能推理** — Thought → Action → Observation → Final Answer 循环，自主决定何时调用工具
- **RAG 混合检索** — 向量语义检索 + 关键词匹配，RRF 融合重排序，支持 `.txt` / `.md` / `.pdf` 上传
- **线索自动捕获** — 识别高意向客户，自动写入 SQLite 数据库
- **后台审计协程** — 异步触发商业线索评分（0-100）与谈判策略分析
- **邮件自动通知** — 捕获高价值线索后 SMTP 实时推送至主管邮箱
- **多租户会话隔离** — WebSocket 按 `session_id` 物理隔离，支持多坐席并发
- **流式输出** — 思考轨迹与最终回答实时推送到前端
- **成本追踪** — 实时计算并展示 API Token 消耗费用（精确到 $0.00001）
- **滑动窗口记忆管理** — 自动裁剪超过 4 轮的历史上下文，控制 Token 开销

## 项目结构

```
├── main.py              # Agent 核心引擎：ReAct 循环、工具调度、RAG 检索
├── server.py            # FastAPI 服务：WebSocket + REST API
├── app.py               # Gradio 前端（可选）
├── database.py          # SQLite 数据库操作（线索 + 聊天记录）
├── prompt.py            # System Prompt 与 Analyst Prompt
├── init_db.py           # ChromaDB 向量知识库初始化脚本
├── index.html           # Vue 3 SPA 前端（推荐）
├── test_ws.html         # WebSocket 调试测试页
├── sales_handbook.txt   # 产品知识库语料（示例）
├── requirements.txt     # Python 依赖
├── .env.example         # 环境变量模板
└── mimo_vector_db/      # ChromaDB 持久化数据（自动生成）
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key 和邮箱配置
```

### 3. 初始化向量知识库

```bash
python init_db.py
```

### 4. 启动后端服务

```bash
python server.py
# 服务运行在 http://127.0.0.1:8000
# 健康检查: http://127.0.0.1:8000/health
```

### 5. 打开前端

**方式 A：Vue SPA（推荐）**

用浏览器直接打开 `index.html`，或使用 VS Code Live Server 插件。

**方式 B：Gradio**

```bash
python app.py
# 自动打开 http://127.0.0.1:7860
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/health` | 健康检查 |
| `POST` | `/api/upload` | 上传知识库文件（.txt / .pdf / .md，最大 10MB） |
| `WS` | `/ws/agent/chat?session_id=xxx` | WebSocket 实时对话 |

### WebSocket 消息格式

**发送：**
```json
{
  "message": "我想了解产品价格",
  "history": []
}
```

**接收（流式）：**
```json
{
  "type": "streaming",
  "log_stream": "思考轮次 [1/5]...",
  "final_answer": "Agent 正在深度思考中...",
  "turn_cost": 0.00012
}
```

**完成：**
```json
{
  "type": "done",
  "content": "推理闭环。"
}
```

## Agent 工具列表

| 工具名 | 触发条件 | 参数 |
|--------|---------|------|
| `Fetch_Product_Knowledge` | 用户询问产品价格、功能、FAQ | `{"query": "关键词"}` |
| `Save_Lead_To_Sheet` | 用户表达购买意向、留下联系方式 | `{"name": "", "contact": "", "intent": ""}` |

## 环境变量说明

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `MIMO_API_KEY` | LLM API Key | - |
| `MIMO_BASE_URL` | LLM API 地址 | - |
| `MIMO_MODEL` | 模型名称 | `mimo-v2.5-pro` |
| `SMTP_SERVER` | 邮件服务器 | - |
| `SMTP_PORT` | 邮件端口 | `465` |
| `SENDER_EMAIL` | 发件人邮箱 | - |
| `SENDER_PWD` | 邮箱授权码 | - |
| `RECEIVER_EMAIL` | 收件人邮箱 | - |
| `ALLOWED_ORIGINS` | CORS 允许的来源 | `*` |

## 技术栈

- **后端**: Python 3.10+ / FastAPI / Uvicorn
- **AI 引擎**: OpenAI Compatible API (ReAct Pattern)
- **向量数据库**: ChromaDB（本地持久化）
- **关系型数据库**: SQLite
- **前端**: Vue 3 / Gradio
- **通信**: WebSocket（全双工） / HTTP REST

## License

MIT
