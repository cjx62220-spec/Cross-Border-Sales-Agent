# server.py
import json
import os
import shutil
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio

# 引入核心处理引擎
from main import run_agent_stream, upload_and_index_file

app = FastAPI(title="Cross-Border Async Multi-Agent Enterprise API", version="5.2.0")

# 🌐 彻底放开跨域，允许 Vue 坐席端无缝调用
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "architecture": "pure_asynchronous", "version": "5.2.0"}


# 🌟 【新接口】提供给 Vue 前端的标准多格式 RAG 文件上传管线
@app.post("/api/upload")
async def upload_handbook_api(file: UploadFile = File(...)):
    """
    异步接收 Vue 前端上传的 .txt/.pdf/.md 手册，
    自动安全的落盘并路由至底层 RAG 切片引擎注入 ChromaDB
    """
    temp_dir = "./temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    file_path = os.path.join(temp_dir, file.filename)
    
    try:
        # 异步流式写入本地临时缓存
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 借用面向对象的鸭子类型，伪造一个带 name 属性的对象传给底层 RAG 引擎
        class MockFileObj:
            def __init__(self, path):
                self.name = path
                
        mock_obj = MockFileObj(file_path)
        # 调用此前写好的自适应多格式解析管道
        result_log = upload_and_index_file(mock_obj)
        
        # 安全擦除临时文件，保持服务器纯净
        if os.path.exists(file_path):
            os.remove(file_path)
            
        if "🟢" in result_log:
            return {"success": true, "message": result_log}
        else:
            return {"success": false, "message": result_log}
            
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return {"success": false, "message": f"服务器网络层写入故障: {str(e)}"}


@app.websocket("/ws/agent/chat")
async def websocket_agent_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 动态隔离会话
    session_id = websocket.query_params.get("session_id", "anonymous_guest")
    print(f"\n[🔌 WebSocket 长连接] 坐席会话激活: {session_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            payload = json.loads(data)
            user_message = payload.get("message", "").strip()
            chat_history = payload.get("history", [])
            
            if not user_message:
                await websocket.send_json({"type": "error", "content": "消息不能为空"})
                continue
                
            print(f"[📥 收到载荷 {session_id}]: '{user_message}'")
            
            # 消费原生异步生成器
            async for log_stream, final_answer, turn_cost in run_agent_stream(
                user_message, chat_history=chat_history, session_id=session_id
            ):
                await websocket.send_json({
                    "type": "streaming",
                    "log_stream": log_stream,
                    "final_answer": final_answer,
                    "turn_cost": round(turn_cost, 5)
                })
                await asyncio.sleep(0.001)
                
            await websocket.send_json({"type": "done", "content": "推理闭环。"})

    except WebSocketDisconnect:
        print(f"[🔌 WebSocket 断开] {session_id} 已安全离线。")
    except Exception as e:
        print(f"[❌ 隧道故障] {session_id} 故障: {str(e)}")
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except:
            pass

if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)