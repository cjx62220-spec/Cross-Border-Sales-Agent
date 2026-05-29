# app.py
import gradio as gr
from main import run_agent

# 1. 定义网页端的对话处理函数
# app.py 中修改后的 predict 函数

def predict(message, history):
    """
    history 是 Gradio 自动维护的列表，格式为 [[用户话1, AI回复1], [用户话2, AI回复2], ...]
    """
    # ➡️ 新增：把整个 history 列表一起传给 run_agent
    agent_response = run_agent(message, chat_history=history)
    
    if not agent_response:
        agent_response = "⚠️ Agent 思考轮数达到上限或发生错误，未能生成最终回复。请查看后台终端日志。"
        
    return agent_response

# 2. 搭建极简却功能强大的 Chat 界面
demo = gr.ChatInterface(
    fn=predict,
    title="🌍 跨境私域智能获客 Agent 运营工作台",
    description="基于 ReAct 架构与本地 ChromaDB 向量知识库。Agent 会自主思考、检索产品手册、并自动将高价值线索录入 CRM。",
    examples=[
        "我想了解一下入手你们那个适合个人外贸做的标准版设备，需要准备多少预算？有啥功能？",
        "你好，我是Jack。我的邮箱是 jack@example.com。我想批量订购 5 台专业版设备，能不能给我打个折？"
    ]
)

# 3. 启动本地 Web 服务器
if __name__ == "__main__":
    print("🚀 正在启动 Gradio 网页端界面...")
    # 启动在本地 7860 端口
    demo.launch(server_name="127.0.0.1", server_port=7860, inbrowser=True)