# 🌍 Cross-Border Sales Agent (跨境私域智能获客与售前助理智能体)

一款基于 **ReAct (Reasoning + Acting) 架构** 与 **ChromaDB 本地向量知识库** 从 0 到 1 打造的垂直领域 AI Agent 系统。专门用于解决跨境电商与海外私域运营中人工回复不及时、高价值外贸线索容易流失的真实业务痛点。

---

## ✨ 核心特性 (Key Features)

* **🧠 自主 ReAct 思考闭环**：摆脱传统的硬编码规则，智能体基于 LLM 动态进行 `Thought -> Action -> Observation -> Final Answer` 的自适应推理流。
* **📚 轻量级本地 RAG**：集成 **ChromaDB 向量数据库**。将企业产品手册及 FAQ 进行语义嵌入（Embedding）存储。Agent 能够自主判断是否检索知识库，消弥大模型幻觉，提供专业外贸话术。
* **📥 自动化线索漏斗（Function Calling）**：内置动态工具链，当用户在多轮对话中展现出明确购买意愿或留下联系方式时，Agent 自动调用结构化工具提取线索，实现从“聊天”到“工作流（Workflow）”的无缝对接。
* **💬 健壮的多轮会话记忆**：完美兼容新版 Gradio 上下文状态机，具备全版本历史记忆适配器，支持长文本跨轮次业务漫游。
* **🛠️ 异常自我修复机制 (Self-Correction)**：对大模型 JSON 输出和异常流量进行了工程化兜底，当格式解析失败时自动将错误回喂给模型进行自我修复。

---

## 📐 系统架构流 (Architecture)

```mermaid
graph TD
    User([海外客户输入]) -->|多轮对话| App[Gradio Web UI 工作台]
    App -->|解析历史上下文| Agent[Agent 核心大脑]
    Agent -->|1. Thought: 思考决策| Decision{是否需要工具?}
    Decision -->|Yes| Action[Action: 动态工具路由]
    Decision -->|No| Final[Final Answer: 组织最终回复]
    Action -->|工具 A| RAG[(ChromaDB 向量知识库)]
    Action -->|工具 B| CRM[(模拟线索入库系统)]
    RAG -->|Observation| Agent
    CRM -->|Observation| Agent
    Final -->|输出人性化响应| User