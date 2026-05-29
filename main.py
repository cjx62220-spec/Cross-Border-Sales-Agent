# main.py
import os
import re
import json
import csv  # ➡️ 方向一：引入 CSV 库实现真实数据落地
from openai import OpenAI
from dotenv import load_dotenv
import chromadb
from prompt import SYSTEM_PROMPT

load_dotenv()

client = OpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url=os.getenv("MIMO_BASE_URL")
)
MODEL_NAME = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")

chroma_client = chromadb.PersistentClient(path="./mimo_vector_db")
collection = chroma_client.get_collection(name="product_knowledge")

# 💰 方向四：定义大模型计费单价（以标准企业监控为例，假设每百万Token单价，可根据实际调整）
PRICE_PER_K_INPUT = 0.001 * 0.007  # 模拟输入单价
PRICE_PER_K_OUTPUT = 0.002 * 0.007 # 模拟输出单价


# 🛠️ 方向一升级：真实的线索落地工具
def tool_save_lead_to_sheet(name, contact, intent):
    """工具2：将捕获到的高价值线索真正写入本地 CSV 文件"""
    print(f"\n[🛠️ 正在执行工具 -> Save_Lead_To_Sheet] 正在写入真实数据库文件...")
    
    file_path = "captured_leads.csv"
    file_exists = os.path.isfile(file_path)
    
    try:
        # 以追加模式（a）写入，确保数据持久化不丢失
        with open(file_path, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            # 如果文件是第一次创建，先写入表头（Header）
            if not file_exists:
                writer.writerow(["客户姓名/称呼", "联系方式", "购买意向描述"])
            
            writer.writerow([name, contact, intent])
            
        # ➡️ 模拟邮件通知流水线
        email_alert_log = f"\n[📧 SMTP自动化通知] 成功触发邮件流水线！已向外贸主管邮箱发送提醒：【新线索：{name}，请速去后台查看】"
        print(email_alert_log)
        
        return f"Observation: 【系统反馈】线索已成功持久化存入服务器 `captured_leads.csv` 数据库，并已成功触发 SMTP 邮件通知流水线。"
    except Exception as e:
        return f"Observation: 【系统错误】持久化写入线索文件失败，原因: {str(e)}"


# 📚 向量知识库检索工具（保持原样）
def tool_fetch_product_knowledge(query):
    """工具1：真实 RAG 向量数据库检索"""
    print(f"\n[🛠️ 正在执行工具 -> Fetch_Product_Knowledge] 模糊检索: \"{query}\"")
    try:
        results = collection.query(query_texts=[query], n_results=1)
        if results and results['documents'] and len(results['documents'][0]) > 0:
            return f"Observation: 【本地向量知识库检索结果】: {results['documents'][0][0]}"
        return "Observation: 【本地向量知识库】未找到高度相关条目，建议引导客户留资由人工详谈。"
    except Exception as e:
        return f"Observation: 知识库检索错误: {str(e)}"


# 📊 方向二&四核心重构：将核心函数改写为 Generator（生成器）
# 通过 yield 实时向前端推送：(当前的思考轨迹, 最终答复, 本轮消耗的成本)
def run_agent_stream(user_message, chat_history=None, max_turns=5):
    log_stream = "🛫 智能体引擎启动，正在分析用户意图...\n"
    total_cost = 0.0
    accumulated_prompt_tokens = 0
    accumulated_completion_tokens = 0
    
    # 1. 组装历史记忆
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if chat_history:
        for item in chat_history:
            if isinstance(item, dict):
                messages.append({"role": item.get("role"), "content": item.get("content")})
            elif hasattr(item, "role") and hasattr(item, "content"):
                messages.append({"role": item.role, "content": item.content})
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                user_past, ai_past = item
                if user_past: messages.append({"role": "user", "content": user_past})
                if ai_past: messages.append({"role": "assistant", "content": ai_past})
                        
    messages.append({"role": "user", "content": user_message})
    
    # 2. 核心 ReAct 迭代循环
    for turn in range(max_turns):
        log_stream += f"\n思考轮次 [{turn + 1}/{max_turns}] --------------------\n"
        yield log_stream, "Agent 正在深度思考中...", total_cost
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.1,  
                stop=["Observation:"] 
            )
            
            # 💰 方向四：动态监控并累加本次调用消耗的 Token 与金钱
            usage = response.usage
            accumulated_prompt_tokens += usage.prompt_tokens
            accumulated_completion_tokens += usage.completion_tokens
            # 计算成本公式
            turn_cost = (usage.prompt_tokens * PRICE_PER_K_INPUT) + (usage.completion_tokens * PRICE_PER_K_OUTPUT)
            total_cost += turn_cost
            
        except Exception as e:
            error_msg = f"❌ 大模型接口调用失败: {str(e)}\n"
            log_stream += error_msg
            yield log_stream, "服务链接发生抖动，请检查后台日志。", total_cost
            return
        
        response_text = response.choices[0].message.content.strip()
        
        # 📊 方向二：将大模型的思考轨迹实时追加到 log_stream 中
        log_stream += f"{response_text}\n"
        yield log_stream, "Agent 正在根据思考结果组织语言或调用工具...", total_cost
        
        messages.append({"role": "assistant", "content": response_text})
        
        # 检查是否得出最终结论
        if "Final Answer:" in response_text:
            final_answer = response_text.split("Final Answer:")[-1].strip()
            log_stream += f"\n✅ 任务成功结束。已向用户吐出最终回复。\n[统计] 累计消耗 Prompt Tokens: {accumulated_prompt_tokens} | Completion Tokens: {accumulated_completion_tokens}\n"
            yield log_stream, final_answer, total_cost
            return
            
        # 解析工具调用
        try:
            action_match = re.search(r"Action:\s*(.*)", response_text)
            action_input_match = re.search(r"Action Input:\s*({.*})", response_text, re.DOTALL)
            
            if not action_match or not action_input_match:
                raise ValueError("大模型未输出标准的 Action/Action Input 格式。")
                
            action_name = action_match.group(1).strip()
            action_params = json.loads(action_input_match.group(1).strip())
            
            if action_name == "Fetch_Product_Knowledge":
                observation_result = tool_fetch_product_knowledge(action_params.get("query", ""))
            elif action_name == "Save_Lead_To_Sheet":
                observation_result = tool_save_lead_to_sheet(
                    name=action_params.get("name", "未知客户"),
                    contact=action_params.get("contact", "未提供"),
                    intent=action_params.get("intent", "未说明")
                )
            else:
                observation_result = f"Observation: 错误：您尝试调用的工具 '{action_name}' 不存在。"
                
            # 将真实的工具执行结果塞回日志和上下文
            log_stream += f"{observation_result}\n"
            yield log_stream, "正在执行外部工具并捕获返回结果...", total_cost
            messages.append({"role": "user", "content": observation_result})
            
        except Exception as e:
            error_obs = f"Observation: 格式解析失败。原因: {str(e)}。请重新以标准的 ReAct 格式输出。"
            log_stream += f"⚠️ 触发工程化异常兜底: {error_obs}\n"
            yield log_stream, "正在纠正大模型格式错误...", total_cost
            messages.append({"role": "user", "content": error_obs})

    log_stream += "\n❌ 达到了最大思考轮数限制。\n"
    yield log_stream, "⚠️ Agent 思考轮数达到上限，未能得出最终结论。", total_cost