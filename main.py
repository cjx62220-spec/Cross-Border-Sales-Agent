# main.py
import os
import re
import json
from openai import OpenAI
from dotenv import load_dotenv
import chromadb  # ➡️ 新增：引入向量数据库库
from prompt import SYSTEM_PROMPT

# 1. 自动加载 .env 文件中的配置
load_dotenv()

# 2. 初始化 MiMO 大模型客户端
client = OpenAI(
    api_key=os.getenv("MIMO_API_KEY"),
    base_url=os.getenv("MIMO_BASE_URL")
)
MODEL_NAME = os.getenv("MIMO_MODEL", "mimo-v2.5-pro")

# 3. 初始化本地向量数据库客户端（连接到我们昨天生成的数据库）
chroma_client = chromadb.PersistentClient(path="./mimo_vector_db")
collection = chroma_client.get_collection(name="product_knowledge")


# 4. 核心业务工具定义（从 Mock 升级为真实 RAG 检索）
def tool_fetch_product_knowledge(query):
    """工具1：真实 RAG 向量数据库检索"""
    print(f"\n[🛠️ 正在执行工具 -> Fetch_Product_Knowledge] 正在向量数据库中模糊检索: \"{query}\"")
    
    try:
        # 使用 ChromaDB 进行语义相似度查询，返回最匹配的一条结果 (n_results=1)
        results = collection.query(
            query_texts=[query],
            n_results=1
        )
        
        # 提取检索到的最相关的文本内容
        if results and results['documents'] and len(results['documents'][0]) > 0:
            matched_text = results['documents'][0][0]
            return f"Observation: 【本地向量知识库检索结果】: {matched_text}"
        else:
            return "Observation: 【本地向量知识库】未找到与该提问高度相关的业务知识，建议引导客户留下联系方式由人工详谈。"
            
    except Exception as e:
        return f"Observation: 知识库检索时发生技术错误: {str(e)}"


def tool_save_lead_to_sheet(name, contact, intent):
    """工具2：模拟将线索写入本地 CRM（保持原样）"""
    print(f"\n[🛠️ 正在执行工具 -> Save_Lead_To_Sheet] 捕获到高价值线索！")
    print(f"   👤 姓名: {name} | 📱 联系方式: {contact} | 🎯 意向: {intent}")
    return "Observation: 【CRM系统反馈】线索已成功保存至后台数据库，并已自动触发自动化流水线分配给专属外贸销售代表。"


# 5. Agent 核心执行循环
# main.py 中修改后的 run_agent 函数

def run_agent(user_message, chat_history=None, max_turns=5):
    print(f"\n================ 🚀 收到用户输入 ================\n用户说: \"{user_message}\"")
    
    # 1. 初始化消息队列，首先塞入全局系统提示词
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    # 2. ➡️ 终极兼容版：智能解析各种历史记忆格式，防止因 Gradio 版本差异引发报错
    if chat_history:
        for item in chat_history:
            # 情况 A：新版 Gradio 的字典格式 {"role": "user", "content": "..."}
            if isinstance(item, dict):
                role = item.get("role")
                content = item.get("content")
                if role and content:
                    messages.append({"role": role, "content": content})
            
            # 情况 B：新版 Gradio 的 ChatMessage 对象
            elif hasattr(item, "role") and hasattr(item, "content"):
                messages.append({"role": item.role, "content": item.content})
            
            # 情况 C：传统旧版 Gradio 的双元素列表格式 [[user_msg, ai_msg], ...]
            elif isinstance(item, (list, tuple)) and len(item) == 2:
                user_past, ai_past = item
                if user_past:
                    messages.append({"role": "user", "content": user_past})
                if ai_past:
                    messages.append({"role": "assistant", "content": ai_past})
                        
    # 3. 最后塞入当前这一轮用户说的话
    messages.append({"role": "user", "content": user_message})
    
    # 4. ReAct 循环控制
    for turn in range(max_turns):
        try:
            # ➡️ 新增：对大模型调用做异常捕获（防止由于网络抖动或API限流导致网页直接红色报错）
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.1,  
                stop=["Observation:"] 
            )
        except Exception as e:
            error_msg = f"❌ 大模型接口调用失败: {str(e)}。请检查网络连接。"
            print(error_msg)
            return error_msg
        
        response_text = response.choices[0].message.content.strip()
        print(f"\n[🤖 Agent 第 {turn + 1} 轮思考与决策]:")
        print(response_text)
        
        messages.append({"role": "assistant", "content": response_text})
        
        if "Final Answer:" in response_text:
            final_answer = response_text.split("Final Answer:")[-1].strip()
            print(f"\n================ ✨ Agent 最终回复 ================\n{final_answer}\n")
            return final_answer
            
        try:
            action_match = re.search(r"Action:\s*(.*)", response_text)
            action_input_match = re.search(r"Action Input:\s*({.*})", response_text, re.DOTALL)
            
            if not action_match or not action_input_match:
                raise ValueError("未检测到标准的 Action 或 Action Input 格式")
                
            action_name = action_match.group(1).strip()
            action_param_str = action_input_match.group(1).strip()
            action_params = json.loads(action_param_str)
            
            # 工具路由
            if action_name == "Fetch_Product_Knowledge":
                observation_result = tool_fetch_product_knowledge(action_params.get("query", ""))
            elif action_name == "Save_Lead_To_Sheet":
                observation_result = tool_save_lead_to_sheet(
                    name=action_params.get("name", "未知客户"),
                    contact=action_params.get("contact", "未提供"),
                    intent=action_params.get("intent", "未说明")
                )
            else:
                observation_result = f"Observation: 错误：您尝试调用的工具 '{action_name}' 不存在，请重新选择。"
                
            print(f"{observation_result}")
            messages.append({"role": "user", "content": observation_result})
            
        except Exception as e:
            error_obs = f"Observation: 格式解析失败。错误原因: {str(e)}。请检查你的输出，确保严格按照 Action: 后面紧跟 Action Input: {{}} 的标准JSON格式重新输出。"
            print(f"\n[⚠️ 触发自我修复机制]: {error_obs}")
            messages.append({"role": "user", "content": error_obs})

    print("\n❌ 达到了最大思考轮数限制，Agent 未能完成任务。")
    return "⚠️ Agent 思考轮数达到上限，未能得出最终结论，请尝试重新提问。"


# 6. 测试用例（运行主函数）
if __name__ == "__main__":
    # 📝 测试语义理解：我们故意不用“价格”或“多少钱”这类字眼，而是用“预算”和“配置”
    run_agent("我想了解一下入手你们那个适合个人外贸做的标准版设备，需要准备多少预算？有啥功能？")