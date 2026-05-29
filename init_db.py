# init_db.py
import chromadb

# 1. 初始化本地持久化向量数据库（它会在本地创建一个叫 mimo_vector_db 的文件夹）
chroma_client = chromadb.PersistentClient(path="./mimo_vector_db")

# 2. 创建或获取一个名为 "product_knowledge" 的集合（类似于数据库里的表）
# ChromaDB 默认会使用内置的轻量级 embedding 模型，无需消耗你的 API 额度
collection = chroma_client.get_or_create_collection(name="product_knowledge")

# 3. 准备一些真实的跨境业务知识库语料
knowledge_data = [
    {
        "id": "faq_001",
        "text": "A款标准版智能网关海外零售价为99美金/台。主要功能包括支持单个 WhatsApp 账号的自动化营销、多语种AI快捷回复回复、以及基础的客户意向度自动打标签。适合初创外贸SOHO个人用户。",
    },
    {
        "id": "faq_002",
        "text": "B款专业版智能网关售价为199美金/台。相比标准版，它支持多账号矩阵风控分流、多渠道线索（包括 WhatsApp、Telegram、Email）聚合管理，支持对接外部企业 CRM 系统，并享有独立专属服务器加速，适合中大型外贸出海团队。",
    },
    {
        "id": "faq_003",
        "text": "关于批量采购优惠：单次订购 10 台以上标准版或专业版设备，可直接享受官方统一 85 折批发价；订购 50 台以上可免费提供一次海外本地化服务器私有部署服务及一年的技术支持。",
    }
]

# 4. 将文本数据塞进向量数据库
collection.add(
    documents=[item["text"] for item in knowledge_data],
    ids=[item["id"] for item in knowledge_data]
)

print("✅ 成功！本地向量知识库已初始化并持久化存储。")
