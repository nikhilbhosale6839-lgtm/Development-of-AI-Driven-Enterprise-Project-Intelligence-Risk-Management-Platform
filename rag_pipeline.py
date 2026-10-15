from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingestion import extract_text
from vector_store import add_documents, search_documents


load_dotenv()


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150
)

llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)


def process_document(file_path, filename):
    """
    Extract text, split into chunks, and index it.
    """

    text = extract_text(file_path)

    chunks = text_splitter.split_text(text)

    if not chunks:
        raise ValueError(
            "Document could not be divided into chunks."
        )

    metadata = {
        "source": filename
    }

    indexed_count = add_documents(
        chunks,
        metadata
    )

    return {
        "filename": filename,
        "total_characters": len(text),
        "total_chunks": len(chunks),
        "indexed_chunks": indexed_count
    }


def ask_question(question):
    """
    Retrieve relevant content and generate an answer.
    """

    question = question.strip()

    if not question:
        raise ValueError(
            "Please enter a question."
        )

    documents = search_documents(
        question,
        k=4
    )

    if not documents:
        return "No relevant documents were found."

    context = "\n\n".join(
        (
            f"Source: {doc.metadata.get('source', 'Unknown')}\n"
            f"Content: {doc.page_content}"
        )
        for doc in documents
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
            You are an AI Project Intelligence Assistant.

            Answer the user's question using the supplied
            project document context.

            Rules:
            - Base your answer on the provided context.
            - Do not invent facts that are not present.
            - If the answer is unavailable in the context,
              clearly state that.
            - Provide a clear, structured answer.
            """
        ),
        (
            "human",
            """
            Project document context:

            {context}

            User question:

            {question}
            """
        )
    ])

    chain = prompt | llm

    response = chain.invoke({
        "context": context,
        "question": question
    })

    return response.content
