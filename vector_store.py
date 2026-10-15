import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings


load_dotenv()

VECTOR_DB_PATH = os.getenv(
    "VECTOR_DB_PATH",
    "vector_db"
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small"
)


def get_vector_store():
    """
    Create or load the persistent Chroma vector database.
    """

    os.makedirs(
        VECTOR_DB_PATH,
        exist_ok=True
    )

    return Chroma(
        collection_name="project_documents",
        embedding_function=embeddings,
        persist_directory=VECTOR_DB_PATH
    )


def add_documents(chunks, metadata):
    """
    Store text chunks and their embeddings.
    """

    if not chunks:
        raise ValueError("No text chunks provided.")

    store = get_vector_store()

    store.add_texts(
        texts=chunks,
        metadatas=[
            metadata.copy()
            for _ in chunks
        ]
    )

    return len(chunks)


def search_documents(query, k=4):
    """
    Retrieve relevant document chunks.
    """

    store = get_vector_store()

    results = store.similarity_search(
        query,
        k=k
    )

    return results
