# main.py
import os
import re
import json
import csv
import smtplib  # ➡️ 引入内置邮件库
from email.mime.text import MIMEText
from email.header import Header
from openai import OpenAI
from dotenv import load_dotenv
import chromadb
from prompt import SYSTEM_PROMPT, ANALYST_PROMPT

load_dotenv()

client = OpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url=os.getenv("MIMO_BASE_URL")
)
MODEL_NAME = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")

chroma_client = chromadb.PersistentClient(path="./mimo_vector_db")
collection = chroma_client.get_collection(name="product_knowledge")

PRICE_PER_K_INPUT = 0.001 * 0.007
PRICE_PER_K_OUTPUT = 0.002 * 0.007

# 📬 真实自动化管线：SMTP 邮件发送引擎
def send_email_alert(lead_name, lead_contact, analysis_report):
    """真正的 SMTP 邮件发送逻辑，内置高级工程降守卫"""
    smtp_server = os.getenv("SMTP_SERVER", "").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    sender_email = os.getenv("SENDER_EMAIL", "").strip()
    sender_pwd = os.getenv("SENDER_PWD", "").strip() # 邮箱授权码
    receiver_email = os.getenv("RECEIVER_EMAIL", "").strip()
    
    # 📝 拼接华丽的 HTML/文本 邮件内容
    email_content = f"""
    ========= 🚨 跨境私域 Agent 捕获高价值线索通知 =========
    【基础留资信息】
    👤 客户称呼: {lead_name}
    📱 联系方式: {lead_contact}
    
    【🕵️‍♂️ 后台合规专家 Agent 深度审计报告】
    🎯 客户画像: {analysis_report.get('customer_profile', '未知')}
    🔥 意向打分: {analysis_report.get('intent_score', '0')}/100
    ⚠️ 风控评级: {analysis_report.get('risk_level', '低')}
    🎯 核心痛点: {analysis_report.get('customer_pain_points', '未指明')}
    💡 谈判与破冰策略: {analysis_report.get('negotiation_strategy', '无')}
    ======================================================
    """
    
    # 🛡️ 工程级守卫：如果没有配置完整的环境变量，自动降级为控制台高亮打印，防止系统闪崩
    if not (smtp_server and sender_email and sender_pwd and receiver_email):
        print(f"\n[⚠️ SMTP安全提示] 邮箱环境变量未配齐，系统自动开启‘安全沙箱模式’模拟发送邮件：{email_content}")
        return "【沙箱运行】邮件已成功生成并安全投递至本地控制台日志中。"
        
    try:
        message = MIMEText(email_content, 'plain', 'utf-8')
        message['From'] = f"MIMO-Agent-System <{sender_email}>"
        message['To'] = f"Sales-Manager <{receiver_email}>"
        message['Subject'] = Header(f"🔥 发现高价值出海客户: {lead_name} (意向分: {analysis_report.get('intent_score', '0')})", 'utf-8')
        
        # 使用 SSL 加密连接服务器
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(sender_email, sender_pwd)
        server.sendmail(sender_email, [receiver_email], message.as_string())
        server.quit()
        print("\n[📧 SMTP自动化通知] 真实邮件已成功冲破物理世界，发送至主管邮箱！")
        return "【SMTP成功】真实分析简报邮件已秒级送达外贸经理邮箱！"
    except Exception as e:
        print(f"\n[❌ SMTP技术故障] 邮件外发失败，原因: {str(e)}")
        return f"【SMTP异常】线索已保存，但邮件外发遇阻: {str(e)}"


# 🛠️ 核心多智能体联动：在这里唤醒第二个 Agent 
def tool_save_lead_to_sheet(name, contact, intent, current_messages_context=None):
    """升级版工具2：在写入线索的同时，驱动黑脸 Agent 进行全量上下文复盘并触发自动化外发"""
    print(f"\n[🛠️ 正在执行工具 -> Save_Lead_To_Sheet] 正在持久化存入线索数据库...")
    
    # 1. 真实的 CSV 落地
    file_path = "captured_leads.csv"
    file_exists = os.path.isfile(file_path)
    try:
        with open(file_path, mode="a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["客户姓名/称呼", "联系方式", "购买意向描述"])
            writer.writerow([name, contact, intent])
    except Exception as e:
        print(f"CSV写入失败: {str(e)}")

    # 2. 🧠 唤醒第二个智能体：B2B商业线索分析专家
    print(f"\n[🧠 Multi-Agent 协作唤醒] -> 正在调度“合规审计专家 Agent”复盘本场会话...")
    
    # 构建第二个智能体的独立上下文（把之前的聊天原封不动地发给合规专家审阅）
    analyst_messages = [{"role": "system", "content": ANALYST_PROMPT}]
    if current_messages_context:
        # 排除掉最开始的第一条全局 system prompt
        analyst_messages.extend(current_messages_context[1:])
    else:
        analyst_messages.append({"role": "user", "content": f"客户称呼: {name}, 留下联系方式: {contact}, 其自述意向: {intent}"})
        
    analysis_json = {}
    try:
        analyst_response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=analyst_messages,
            temperature=0.1,
            response_format={"type": "json_object"} # 强迫大模型直接吐出纯净的 JSON 对象
        )
        analysis_res_text = analyst_response.choices[0].message.content.strip()
        analysis_json = json.loads(analysis_res_text)
        print(f"[✅ 合规专家 Agent 审计完成] 意向评分: {analysis_json.get('intent_score', '0')}分 | 风控级: {analysis_json.get('risk_level', '未知')}")
    except Exception as e:
        print(f"合规专家 Agent 审计异常: {str(e)}")
        analysis_json = {"customer_profile": "解析失败", "intent_score": 50, "risk_level": "高", "customer_pain_points": "未知", "negotiation_strategy": "保持常规跟进"}

    # 3. 📬 推动自动化物理管道：把线索和审计结果做成邮件发出去
    email_status = send_email_alert(name, contact, analysis_json)
    
    # 把第二个 Agent 得出的硬核结论，作为 Observation 强行喂给前端的一线销售 Agent 听
    observation_feedback = f"Observation: 【Multi-Agent 协同闭环反馈】线索已记入表格。后台专家审计意向分为【{analysis_json.get('intent_score', 0)}分】，判定风控级别为【{analysis_json.get('risk_level', '低')}】。{email_status} 请您立刻以极其热情的姿态礼貌地向客户致谢并结束本次精彩的售前会话。"
    return observation_feedback


def tool_fetch_product_knowledge(query):
    try:
        results = collection.query(query_texts=[query], n_results=1)
        if results and results['documents'] and len(results['documents'][0]) > 0:
            return f"Observation: 【本地向量知识库检索结果】: {results['documents'][0][0]}"
        return "Observation: 【本地向量知识库】未找到高度相关条目，建议引导客户留资由人工详谈。"
    except Exception as e:
        return f"Observation: 知识库检索错误: {str(e)}"


# 生成器核心引擎（只修改了工具调用的传参部分）
def run_agent_stream(user_message, chat_history=None, max_turns=5):
    log_stream = "🛫 智能体引擎启动，正在分析用户意图...\n"
    total_cost = 0.0
    accumulated_prompt_tokens = 0
    accumulated_completion_tokens = 0
    
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
            usage = response.usage
            accumulated_prompt_tokens += usage.prompt_tokens
            accumulated_completion_tokens += usage.completion_tokens
            turn_cost = (usage.prompt_tokens * PRICE_PER_K_INPUT) + (usage.completion_tokens * PRICE_PER_K_OUTPUT)
            total_cost += turn_cost
        except Exception as e:
            error_msg = f"❌ 大模型接口调用失败: {str(e)}\n"
            log_stream += error_msg
            yield log_stream, "服务链接发生抖动，请检查后台日志。", total_cost
            return
        
        response_text = response.choices[0].message.content.strip()
        log_stream += f"{response_text}\n"
        yield log_stream, "Agent 正在根据思考结果组织语言或调用工具...", total_cost
        messages.append({"role": "assistant", "content": response_text})
        
        if "Final Answer:" in response_text:
            final_answer = response_text.split("Final Answer:")[-1].strip()
            log_stream += f"\n✅ 任务成功结束。\n[统计] 累计消耗 Prompt Tokens: {accumulated_prompt_tokens} | Completion Tokens: {accumulated_completion_tokens}\n"
            yield log_stream, final_answer, total_cost
            return
            
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
                # ➡️ 核心变化：将当前大模型吃过的所有 messages 历史，作为上下文直接拍给第二个 Agent 去审计！
                observation_result = tool_save_lead_to_sheet(
                    name=action_params.get("name", "未知客户"),
                    contact=action_params.get("contact", "未提供"),
                    intent=action_params.get("intent", "未说明"),
                    current_messages_context=messages 
                )
            else:
                observation_result = f"Observation: 错误：您尝试调用的工具 '{action_name}' 不存在。"
                
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