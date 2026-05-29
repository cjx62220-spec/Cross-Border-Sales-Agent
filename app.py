# app.py
import gradio as gr
import uuid
import os
from main import run_agent_stream, collection

# 1. 动态 RAG 文件解析器逻辑
def upload_and_index_file(file_obj):
    if file_obj is None:
        return "❌ 索引失败：请先选择一个有效的 .txt 文件上传！"
    try:
        with open(file_obj.name, "r", encoding="utf-8") as f:
            text_content = f.read()
        
        chunks = [c.strip() for c in text_content.split("\n\n") if c.strip()]
        if not chunks:
            chunks = [c.strip() for c in text_content.split("\n") if c.strip()]
        if not chunks:
            return "⚠️ 警告：上传的文件 seem to be empty。"
            
        ids = [f"dynamic_upload_{uuid.uuid4().hex[:8]}" for _ in chunks]
        collection.add(documents=chunks, ids=ids)
        return f"🔥 [RAG流水线成功] 动态解析完成！成功将文档切分为 {len(chunks)} 个语义片段并注入本地 ChromaDB 向量库。"
    except Exception as e:
        return f"❌ 向量化过程中发生系统技术错误: {str(e)}"


# 2. ➡️ 核心重构：多格式自适应的流式对话控制中心
def bot_chat_stream(history, accumulated_cost):
    if not history:
        yield history, "💬 等待用户输入消息...", accumulated_cost, accumulated_cost
        return
        
    # 🕵️‍♂️ 动态探测当前的历史数据格式
    first_item = history[0]
    is_dict = isinstance(first_item, dict)
    is_obj = hasattr(first_item, "role") and hasattr(first_item, "content")
    
    # 根据不同格式，精准提取当前这一轮用户刚输入的文本，并优雅地追加 assistant 占位符
    if is_dict:
        user_message = history[-1]["content"]
        history.append({"role": "assistant", "content": "思考中..."})
        past_history = history[:-2]  # 喂给大模型的历史：排除刚加的user和assistant占位符
    elif is_obj:
        user_message = history[-1].content
        from gradio.components.chatbot import ChatMessage
        history.append(ChatMessage(role="assistant", content="思考中..."))
        past_history = history[:-2]
    else:
        user_message = history[-1][0]
        past_history = history[:-1]
    
    # 启动 main.py 里的流式控制引擎
    agent_generator = run_agent_stream(user_message, chat_history=past_history)
    
    for log_stream, final_answer, turn_cost in agent_generator:
        # 根据格式，流式更新最后一轮回复的文本内容
        if is_dict:
            history[-1]["content"] = final_answer
        elif is_obj:
            history[-1].content = final_answer
        else:
            history[-1][1] = final_answer
        
        total_current_cost = accumulated_cost + turn_cost
        yield history, log_stream, round(total_current_cost, 5), total_current_cost


# ➡️ 核心重构：自适应追加用户消息
def user_send_message(user_msg, history):
    if not user_msg.strip():
        return "", history
    
    # 如果是全新的对话，现代 Gradio (4.x/5.x) 强力推荐使用字典流控制
    if not history:
        return "", [{"role": "user", "content": user_msg}]
    
    # 如果已经有历史，根据历史的第一条数据的类型来决定用什么格式追加
    first_item = history[0]
    if isinstance(first_item, dict):
        history.append({"role": "user", "content": user_msg})
        return "", history
    elif hasattr(first_item, "role") and hasattr(first_item, "content"):
        from gradio.components.chatbot import ChatMessage
        history.append(ChatMessage(role="user", content=user_msg))
        return "", history
    else:
        # 老版本列表元组格式降级兼容
        return "", history + [[user_msg, None]]


def clear_console():
    return [], "🟢 系统已重置，会话状态与单次成本计数器已归零。验证就绪。", 0.0, 0.0


# 3. 三栏式大屏 UI 布局保持原样
with gr.Blocks(title="跨境私域 Agent 运营工作台 V2.0") as demo:
    gr.Markdown("# 🌍 跨境私域智能获客 Agent 企业级全栈控制台 (Enterprise Console)")
    gr.Markdown("展示完整的 **ReAct 状态机可观测性 (Observability)**、**动态 RAG 管道数据落地** 以及 **大模型分布式成本监控 (FinOps)**。")
    
    with gr.Row():
        cost_monitor = gr.Number(label="💰 本次会话全局累计已消耗 API 成本 ($)", value=0.0, precision=5, interactive=False)
        db_status = gr.Textbox(label="📊 后台系统状态雷达", value="🟢 系统运转良好。本地 ChromaDB 与线索 CSV 数据库已就绪。", interactive=False)
    
    session_cost_state = gr.State(value=0.0)
    
    with gr.Row():
        # 栏目一：左侧 📚 动态 RAG 面板
        with gr.Column(scale=1):
            gr.Markdown("### 📥 动态知识库注入 (RAG Pipeline)")
            file_uploader = gr.File(label="上传企业最新产品手册/FAQ (.txt)", file_types=[".txt"])
            upload_run_btn = gr.Button("🔥 立即解析并同步至向量数据库", variant="primary")
            upload_logs = gr.Textbox(label="向量流水线后台日志", lines=8, interactive=False, placeholder="上传文件并点击上方按钮后...")
            gr.Markdown("<br>💡 *Tip: 你可以直接上传刚刚创建的 `sales_handbook.txt`。*")
            
        # 栏目二：中间 💬 智能售前对话工作台
        with gr.Column(scale=2):
            gr.Markdown("### 💬 智能客服终端 (Chat Interface)")
            chat_box = gr.Chatbot(label="出海私域真实客户会话窗口")
            user_input = gr.Textbox(label="模拟海外客户输入...", placeholder="在此输入客户提问...")
            with gr.Row():
                send_btn = gr.Button("发送消息", variant="primary")
                reset_btn = gr.Button("清空对话与监控看板")
                
        # 栏目三：右侧 🤖 Agent 监控后台
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 智能体思维轨迹 (Observability)")
            console_window = gr.Textbox(label="Agent 实时监控日志流", lines=21, max_lines=30, interactive=False, placeholder="此处将流式展示思维轨迹...")

    # 事件绑定
    send_btn.click(user_send_message, inputs=[user_input, chat_box], outputs=[user_input, chat_box], queue=False).then(
        bot_chat_stream, inputs=[chat_box, session_cost_state], outputs=[chat_box, console_window, cost_monitor, session_cost_state]
    )
    user_input.submit(user_send_message, inputs=[user_input, chat_box], outputs=[user_input, chat_box], queue=False).then(
        bot_chat_stream, inputs=[chat_box, session_cost_state], outputs=[chat_box, console_window, cost_monitor, session_cost_state]
    )
    upload_run_btn.click(upload_and_index_file, inputs=[file_uploader], outputs=[upload_logs])
    reset_btn.click(clear_console, inputs=[], outputs=[chat_box, db_status, cost_monitor, session_cost_state])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)
    