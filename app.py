# app.py
import gradio as gr
import uuid
import os
from main import run_agent_stream, collection

# 🌟 V4.2 新增：多格式非结构化数据自适应解析引擎
def extract_text_from_file(file_path):
    """根据文件后缀动态路由解析器，完美提取干净的文本内容"""
    ext = os.path.splitext(file_path)[1].lower()
    
    # 1. 针对纯文本与 Markdown
    if ext in [".txt", ".md"]:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
            
    # 2. 针对企业级 PDF 文档
    elif ext == ".pdf":
        try:
            import pypdf
            reader = pypdf.PdfReader(file_path)
            extracted_text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    # 自动注入页码标记，方便 RAG 检索时追溯源头
                    extracted_text += f"\n[Page {i+1}]\n" + page_text
            return extracted_text
        except ImportError:
            raise ImportError("⚠️ 检测到 PDF 文件，但本地未安装 pypdf 库。请在终端执行 'pip install pypdf' 后重试！")
        except Exception as e:
            raise RuntimeError(f"PDF 解析发生技术故障: {str(e)}")
            
    # 3. 格式安全防御隔离
    else:
        raise ValueError(f"⚠️ 暂不支持 {ext} 格式。为了确保向量检索精度，目前仅支持 .txt, .md, .pdf 格式产品手册。")


# 🧬 动态 RAG 异步同步管线（升级版）
def upload_and_index_file(file_obj):
    if file_obj is None:
        return "❌ 未选择文件"
    try:
        # 兼容处理高版本 Gradio 传入的对象路径
        file_path = file_obj.name if hasattr(file_obj, "name") else str(file_obj)
        file_name = os.path.basename(file_path)
        
        # ➡️ 核心大招：调用多格式自适应解析引擎
        text_content = extract_text_from_file(file_path)
        
        # 智能文本清洗与两级智能切片机制（按段落或换行）
        chunks = [c.strip() for c in text_content.split("\n\n") if c.strip()]
        if not chunks:
            chunks = [c.strip() for c in text_content.split("\n") if c.strip()]
        if not chunks:
            return "⚠️ 文件解析为空，未检测到有效文本内容。"
            
        # 批量生成具备全网唯一性的持久化 UUID 向量主键
        ids = [f"dynamic_upload_{uuid.uuid4().hex[:8]}" for _ in chunks]
        
        # 注入 ChromaDB 本地持久化向量数据库
        collection.add(documents=chunks, ids=ids)
        return f"🟢 [RAG多格式解析成功] 源文件: {file_name} | 成功切分 {len(chunks)} 个片段注入知识库。"
    except Exception as e:
        return f"❌ 错误: {str(e)}"


# 2. 流式对话控制中心
def bot_chat_stream(history, accumulated_cost):
    if not history:
        yield history, "💬 等待输入...", accumulated_cost, accumulated_cost
        return
        
    first_item = history[0]
    is_dict = isinstance(first_item, dict)
    is_obj = hasattr(first_item, "role") and hasattr(first_item, "content")
    
    if is_dict:
        user_message = history[-1]["content"]
        history.append({"role": "assistant", "content": "🧬 正在检索多格式知识库并深度思考..."})
        past_history = history[:-2]
    elif is_obj:
        user_message = history[-1].content
        from gradio.components.chatbot import ChatMessage
        history.append(ChatMessage(role="assistant", content="🧬 正在检索多格式知识库并深度思考..."))
        past_history = history[:-2]
    else:
        user_message = history[-1][0]
        past_history = history[:-1]
    
    agent_generator = run_agent_stream(user_message, chat_history=past_history)
    
    for log_stream, final_answer, turn_cost in agent_generator:
        if is_dict:
            history[-1]["content"] = final_answer
        elif is_obj:
            history[-1].content = final_answer
        else:
            history[-1][1] = final_answer
        
        total_current_cost = accumulated_cost + turn_cost
        yield history, log_stream, round(total_current_cost, 5), total_current_cost

def user_send_message(user_msg, history):
    if not user_msg.strip():
        return "", history
    if not history:
        return "", [{"role": "user", "content": user_msg}]
    
    first_item = history[0]
    if isinstance(first_item, dict):
        history.append({"role": "user", "content": user_msg})
        return "", history
    elif hasattr(first_item, "role") and hasattr(first_item, "content"):
        from gradio.components.chatbot import ChatMessage
        history.append(ChatMessage(role="user", content=user_msg))
        return "", history
    else:
        return "", history + [[user_msg, None]]

def clear_console():
    return [], "🟢 系统状态重置成功。", 0.0, 0.0


# 🎨 ====== Apple 官网级高级自适应 CSS ======
apple_css = """
body, .gradio-container {
    background-color: #f5f5f7 !important;
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", Arial, sans-serif !important;
}
.gradio-block {
    background-color: #ffffff !important;
    border: none !important;
    border-radius: 16px !important;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.02) !important;
    padding: 20px !important;
}
.stat-card {
    background-color: #ffffff !important;
    border: none !important;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.01) !important;
}
.fieldset, .form {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
.chatbot .message-wrap .message.user {
    background-color: #0071e3 !important;
    color: #ffffff !important;
    border-radius: 18px !important;
}
.chatbot .message-wrap .message.assistant {
    background-color: #e5e5ea !important;
    color: #1d1d1f !important;
    border-radius: 18px !important;
}
.terminal-console textarea {
    background-color: #f5f5f7 !important;
    color: #1d1d1f !important;
    font-family: "SF Mono", "Fira Code", monospace !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 16px !important;
    box-shadow: none !important;
}
input[type="text"] {
    background-color: #f5f5f7 !important;
    border: none !important;
    border-radius: 24px !important;
    padding: 12px 20px !important;
}
.btn-apple-blue {
    background-color: #0071e3 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 24px !important;
    font-weight: 500 !important;
}
.btn-apple-gray {
    background-color: #e5e5ea !important;
    color: #1d1d1f !important;
    border: none !important;
    border-radius: 24px !important;
}
"""

theme = gr.themes.Soft(
    primary_hue="blue",
    secondary_hue="neutral",
    neutral_hue="neutral"
)

with gr.Blocks(title="Cross-Border Sales Console") as demo:
    
    with gr.Row():
        with gr.Column(scale=4):
            gr.Markdown("<h1 style='color: #1d1d1f; font-weight: 600; font-size: 25px; margin-bottom: 2px; letter-spacing: -0.5px;'>Cross-Border Sales Console</h1>")
            gr.Markdown("<p style='color: #86868b; font-size: 13px; margin-top: 0;'>Enterprise Solution • Multi-Agent Automation Framework</p>")
        with gr.Column(scale=1):
            reset_btn = gr.Button("🔄 Reset Console", elem_classes="btn-apple-gray")
            
    gr.Markdown("<hr style='border: 0; height: 1px; background: #e5e5e7; margin: 12px 0 20px 0;'>")
            
    with gr.Row():
        with gr.Column(scale=1):
            cost_monitor = gr.Number(
                label="Total API Cost ($)", 
                show_label=True, 
                value=0.0, 
                precision=5, 
                interactive=False,
                elem_classes="stat-card"
            )
        with gr.Column(scale=2):
            db_status = gr.Textbox(
                label="System Radar Overview", 
                show_label=True,
                value="🟢 Operational. Sub-threads Active. Multi-Format RAG Engine Engaged.", 
                interactive=False,
                elem_classes="stat-card"
            )
            
    session_cost_state = gr.State(value=0.0)
    
    with gr.Row():
        with gr.Column(scale=3):
            gr.Markdown("<h3 style='color: #1d1d1f; font-size: 15px; font-weight: 500; margin-bottom: 8px;'>💬 Interactive Terminal</h3>")
            chat_box = gr.Chatbot(show_label=False, height=440)
            
            with gr.Row():
                user_input = gr.Textbox(
                    scale=5,
                    show_label=False,
                    placeholder="Type a message or enter customer intent...",
                    container=False
                )
                send_btn = gr.Button("Send", scale=1, elem_classes="btn-apple-blue")
            
            # 🌟 RAG 区域：UploadButton 此时已解除封印，完美支持 .txt, .md, .pdf
            gr.Markdown("<br><h3 style='color: #1d1d1f; font-size: 15px; font-weight: 500; margin-bottom: 8px;'>📚 Context Synchronization (RAG Pipeline)</h3>")
            with gr.Row():
                file_uploader = gr.UploadButton(
                    "📎 Choose Handbook (.txt/.pdf/.md)", 
                    file_types=[".txt", ".pdf", ".md"], 
                    scale=2,
                    elem_classes="btn-apple-gray"
                )
                upload_run_btn = gr.Button("Sync Memory", scale=2, elem_classes="btn-apple-blue")
                upload_logs = gr.Textbox(
                    scale=3,
                    show_label=False,
                    interactive=False, 
                    placeholder="Pipeline idle...",
                    container=False
                )

        with gr.Column(scale=1):
            gr.Markdown("<h3 style='color: #1d1d1f; font-size: 15px; font-weight: 500; margin-bottom: 8px;'>🤖 Agent Observability</h3>")
            console_window = gr.Textbox(
                show_label=False, 
                lines=28, 
                interactive=False,
                elem_classes="terminal-console",
                placeholder="Awaiting state machine activation..."
            )

    # 🔗 并发管线事件绑定
    send_btn.click(
        user_send_message, inputs=[user_input, chat_box], outputs=[user_input, chat_box], queue=False
    ).then(
        bot_chat_stream, inputs=[chat_box, session_cost_state], outputs=[chat_box, console_window, cost_monitor, session_cost_state]
    )
    
    user_input.submit(
        user_send_message, inputs=[user_input, chat_box], outputs=[user_input, chat_box], queue=False
    ).then(
        bot_chat_stream, inputs=[chat_box, session_cost_state], outputs=[chat_box, console_window, cost_monitor, session_cost_state]
    )
    
    file_uploader.upload(upload_and_index_file, inputs=[file_uploader], outputs=[upload_logs])
    upload_run_btn.click(lambda: "💡 提示：文件选择后已自动秒级同步，无需重复点击。", outputs=[upload_logs])
    reset_btn.click(clear_console, inputs=[], outputs=[chat_box, db_status, cost_monitor, session_cost_state])

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True, theme=theme, css=apple_css)