"""app/core/rag.py — LangChain Qdrant Vector Store & Google Embeddings RAG Integration"""

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()


def get_vector_store() -> QdrantVectorStore:
    """Initializes and returns the LangChain Qdrant vector store using Google embeddings."""
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=settings.gemini_api_key
    )

    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key
    )

    # Ensure collection exists
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    
    if settings.qdrant_collection_name not in collection_names:
        client.create_collection(
            collection_name=settings.qdrant_collection_name,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
        logger.info("qdrant_collection_created", collection=settings.qdrant_collection_name)

    return QdrantVectorStore(
        client=client,
        collection_name=settings.qdrant_collection_name,
        embedding=embeddings
    )


async def hybrid_corporate_search(query: str, k: int = 3) -> list[dict]:
    """Performs semantic similarity search across internal corporate playbooks and product catalogs."""
    try:
        vector_store = get_vector_store()
        docs = vector_store.similarity_search(query, k=k)
        
        return [
            {
                "source": doc.metadata.get("source", "internal_playbook"),
                "content": doc.page_content
            }
            for doc in docs
        ]
    except Exception as e:
        logger.exception("qdrant_rag_search_failed", error=str(e))
        return []
