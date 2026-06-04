# main.py
import os
import re
import json
import asyncio
import smtplib
import uuid
from email.mime.text import MIMEText
from openai import AsyncOpenAI
from dotenv import load_dotenv
import chromadb
from prompt import SYSTEM_PROMPT, ANALYST_PROMPT
from database import init_database, save_lead_to_db, save_chat_message

load_dotenv()
init_database()

# 初始化异步大模型客户端
client = AsyncOpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url=os.getenv("MIMO_BASE_URL")
)
MODEL_NAME = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")

chroma_client = chromadb.PersistentClient(path="./mimo_vector_db")
collection = chroma_client.get_collection(name="product_knowledge")

# 价格常量（可通过环境变量覆盖）
PRICE_PER_K_INPUT = float(os.getenv("PRICE_PER_K_INPUT", "0.000007"))
PRICE_PER_K_OUTPUT = float(os.getenv("PRICE_PER_K_OUTPUT", "0.000014"))

# 后台审计任务引用集合（防止 asyncio.create_task 被 GC 回收）
_background_tasks: set[asyncio.Task] = set()


# 🌟 多格式非结构化数据自适应解析引擎
def extract_text_from_file(file_path):
    """根据文件后缀动态路由解析器，完美提取干净的文本内容"""
    ext = os.path.splitext(file_path)[1].lower()

    if ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            extracted_text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    extracted_text += f"\n[Page {i+1}]\n" + page_text
            return extracted_text
        except ImportError:
            raise ImportError("⚠️ 检测到 PDF 文件，但本地未安装 pypdf 库。请执行 'pip install pypdf' 后重试！")
        except Exception as e:
            raise RuntimeError(f"PDF 解析发生技术故障: {str(e)}")
    else:
        raise ValueError(f"⚠️ 暂不支持 {ext} 格式。目前仅支持 .txt, .md, .pdf 格式。")


# 🌟 动态 RAG 向量注入管线
def upload_and_index_file(file_obj):
    if file_obj is None:
        return "❌ 未选择文件"
    try:
        file_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
        file_name = os.path.basename(file_path)

        text_content = extract_text_from_file(file_path)

        # 智能切片机制
        chunks = [c.strip() for c in text_content.split("\n\n") if c.strip()]
        if not chunks:
            chunks = [c.strip() for c in text_content.split("\n") if c.strip()]
        if not chunks:
            return "⚠️ 文件解析为空，未检测到有效文本内容。"

        ids = [f"dynamic_upload_{uuid.uuid4().hex[:8]}" for _ in chunks]
        collection.add(documents=chunks, ids=ids)
        return f"🟢 [RAG多格式解析成功] 源文件: {file_name} | 成功切分 {len(chunks)} 个片段注入知识库。"
    except Exception as e:
        return f"❌ 错误: {str(e)}"


# 🧠 工业级会话记忆滑动窗口管理器
def manage_context_window(chat_history, max_keep_turns=4):
    if not chat_history:
        return []
    if len(chat_history) > max_keep_turns:
        print(f"\n[🧠 记忆管理器] 触发滑动窗口压缩，保留最近 {max_keep_turns} 轮上下文。")
        return chat_history[-max_keep_turns:]
    return chat_history


# 📬 异步 SMTP 邮件外发（线程池包装）
def send_email_sync(lead_name, lead_contact, analysis_report):
    smtp_server = os.getenv("SMTP_SERVER", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    sender_email = os.getenv("SENDER_EMAIL", "").strip()
    sender_pwd = os.getenv("SENDER_PWD", "").strip()
    receiver_email = os.getenv("RECEIVER_EMAIL", "").strip()

    email_content = f"""
    ========= 🚨 跨境私域 Agent 捕获高价值线索通知 =========
    👤 客户称呼: {lead_name} | 联系方式: {lead_contact}
    🔥 意向打分: {analysis_report.get('intent_score', '0')}/100
    🎯 核心痛点: {analysis_report.get('customer_pain_points', '未指明')}
    ======================================================
    """
    if not (smtp_server and sender_email and sender_pwd and receiver_email):
        print(f"\n[⚠️ SMTP提示] 邮箱未配齐，沙箱模拟输出：{email_content}")
        return
    try:
        message = MIMEText(email_content, 'plain', 'utf-8')
        message['From'] = f"MIMO-Agent-System <{sender_email}>"
        message['To'] = f"Sales-Manager <{receiver_email}>"
        message['Subject'] = f"🔥 [协程并发] 发现高价值出海客户: {lead_name}"

        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_pwd)
        server.sendmail(sender_email, [receiver_email], message.as_string())
        server.quit()
        print("\n[📧 SMTP自动化通知] 异步协程邮件外发成功！")
    except Exception as e:
        print(f"\n[❌ SMTP技术故障] 邮件外发失败: {str(e)}")


# 🕵️‍♂️ 纯异步黑脸专家审计任务
async def bg_async_audit_task(name, contact, intent, messages_context):
    print(f"\n[⚡ 协程异步任务启动] 后台专家开始审计...")
    analyst_messages = [{"role": "system", "content": ANALYST_PROMPT}]
    if messages_context:
        analyst_messages.extend(messages_context[1:])
    else:
        analyst_messages.append({"role": "user", "content": f"客户: {name}, 联系方式: {contact}"})

    try:
        analyst_response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=analyst_messages,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        analysis_json = json.loads(analyst_response.choices[0].message.content.strip())
        print(f"[⚡ 协程审计成功] 审计得分: {analysis_json.get('intent_score', '0')}")

        await asyncio.to_thread(send_email_sync, name, contact, analysis_json)
    except Exception as e:
        print(f"[❌ 协程审计异常] : {str(e)}")


# 🛠️ 纯异步工具集成
async def tool_save_lead_to_db_async(name, contact, intent, current_messages_context=None):
    print(f"\n[🛠️ 执行工具 -> Save_Lead_To_Sheet] 异步写入 SQL 数据库...")
    await asyncio.to_thread(save_lead_to_db, name, contact, intent)
    context_snapshot = list(current_messages_context) if current_messages_context else None

    # 保存 task 引用，防止被 GC 回收
    task = asyncio.create_task(bg_async_audit_task(name, contact, intent, context_snapshot))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return "Observation: 【系统反馈】线索已安全写入数据库，后台非阻塞协程审计任务已并发挂起。"


def tool_fetch_product_knowledge(query):
    """混合检索：向量语义检索 + 关键词匹配，RRF 重排"""
    try:
        # 向量语义检索
        vector_results = collection.query(query_texts=[query], n_results=5)
        vector_docs = vector_results['documents'][0] if (vector_results and vector_results['documents']) else []

        # 关键词匹配（基于向量库中已有结果，避免全量拉取）
        clean_keywords = [kw.lower() for kw in re.split(r'\s+|的|了|想问|关于|咨询', query) if kw.strip()]
        keyword_docs = [doc for doc in vector_docs if any(kw in doc.lower() for kw in clean_keywords)]

        # RRF 重排
        rrf_scores = {}
        for rank, doc in enumerate(vector_docs):
            rrf_scores[doc] = rrf_scores.get(doc, 0.0) + 1.0 / (60 + (rank + 1))
        for rank, doc in enumerate(keyword_docs):
            rrf_scores[doc] = rrf_scores.get(doc, 0.0) + 1.0 / (60 + (rank + 1))

        if not rrf_scores:
            return "Observation: 【本地向量知识库】未找到高度相关条目。"

        sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
        return f"Observation: 【混合检索与RRF重排结果】: {sorted_docs[0][0]}"
    except Exception as e:
        return f"Observation: 检索故障: {str(e)}"


# 🚀 全新原生异步生成器
async def run_agent_stream(user_message, chat_history=None, max_turns=5, session_id="default_session"):
    log_stream = "🛫 智能体原生异步引擎启动...\n"
    total_cost = 0.0
    accumulated_prompt_tokens = 0
    accumulated_completion_tokens = 0

    await asyncio.to_thread(save_chat_message, session_id, "user", user_message)

    secured_history = manage_context_window(chat_history, max_keep_turns=4)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if secured_history:
        for item in secured_history:
            if isinstance(item, dict):
                messages.append({"role": item.get("role"), "content": item.get("content")})
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                user_past, ai_past = item
                if user_past:
                    messages.append({"role": "user", "content": user_past})
                if ai_past:
                    messages.append({"role": "assistant", "content": ai_past})

    messages.append({"role": "user", "content": user_message})

    for turn in range(max_turns):
        log_stream += f"\n思考轮次 [{turn + 1}/{max_turns}] --------------------\n"
        yield log_stream, "Agent 正在深度思考中...", total_cost

        try:
            response = await client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.1,
                stop=["Observation:"]
            )
            usage = response.usage
            accumulated_prompt_tokens += usage.prompt_tokens
            accumulated_completion_tokens += usage.completion_tokens
            total_cost += (usage.prompt_tokens * PRICE_PER_K_INPUT) + (usage.completion_tokens * PRICE_PER_K_OUTPUT)
        except Exception as e:
            yield log_stream + f"❌ 调用失败: {str(e)}\n", "服务连接抖动。", total_cost
            return

        response_text = response.choices[0].message.content.strip()
        log_stream += f"{response_text}\n"
        yield log_stream, "Agent 正在组织语言或调用工具...", total_cost
        messages.append({"role": "assistant", "content": response_text})

        if "Final Answer:" in response_text:
            final_answer = response_text.split("Final Answer:")[-1].strip()
            log_stream += f"\n✅ 任务结束。Prompt Tokens: {accumulated_prompt_tokens} | Completion Tokens: {accumulated_completion_tokens}\n"

            await asyncio.to_thread(save_chat_message, session_id, "assistant", final_answer)
            yield log_stream, final_answer, total_cost
            return

        try:
            action_match = re.search(r"Action:\s*(.*)", response_text)
            action_input_match = re.search(r"Action Input:\s*({.*})", response_text, re.DOTALL)

            if not action_match or not action_input_match:
                raise ValueError("未输出标准的 ReAct 格式。")

            action_name = action_match.group(1).strip()
            action_params = json.loads(action_input_match.group(1).strip())

            if action_name == "Fetch_Product_Knowledge":
                observation_result = await asyncio.to_thread(tool_fetch_product_knowledge, action_params.get("query", ""))
            elif action_name == "Save_Lead_To_Sheet":
                observation_result = await tool_save_lead_to_db_async(
                    name=action_params.get("name", "未知客户"),
                    contact=action_params.get("contact", "未提供"),
                    intent=action_params.get("intent", "未说明"),
                    current_messages_context=messages
                )
            else:
                observation_result = f"Observation: 工具 '{action_name}' 不存在。"

            log_stream += f"{observation_result}\n"
            yield log_stream, "正在捕获返回结果...", total_cost
            messages.append({"role": "user", "content": observation_result})

        except Exception as e:
            error_obs = f"Observation: 格式错误. 原因: {str(e)}. 请重试。"
            log_stream += f"⚠️ 触发异常兜底: {error_obs}\n"
            yield log_stream, "正在纠正格式错误...", total_cost
            messages.append({"role": "user", "content": error_obs})
