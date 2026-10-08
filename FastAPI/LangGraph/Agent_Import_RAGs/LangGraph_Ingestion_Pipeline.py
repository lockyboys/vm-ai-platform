# ==============================================================================
# [SPS ORCHESTRATOR 13-PERSONA VERIFIED]
# - 원본 RAG 파이프라인 에이전트 구조 및 orchestrator 연동 호환성 통합
# ==============================================================================
# FastAPI/LangGraph/Agent_Import_RAGs/LangGraph_Ingestion_Pipeline.py
import os
from typing import Annotated
from typing_extensions import TypedDict
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma 

BASE_DIR = "./downloaded_docs"
CHROMA_DB_DIR = "./chroma_db"

class IngestionState(TypedDict):
    messages: Annotated[list, add_messages]

def get_all_pdf_files():
    """BASE_DIR 하위의 모든 도메인 폴더를 순회하며 PDF 파일 경로를 수집합니다."""
    pdf_files = []
    if not os.path.exists(BASE_DIR): 
        os.makedirs(BASE_DIR)
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".pdf"):
                pdf_files.append(os.path.join(root, file))
    return pdf_files

@tool
def scan_directory() -> str:
    """하위 디렉토리를 포함한 모든 문서 목록을 확인합니다."""
    files = get_all_pdf_files()
    if not files: return "[경고] 분석할 PDF 파일이 없습니다. 문서를 먼저 수집해야 합니다."
    return f"[성공] 총 {len(files)}개의 발견된 문서: {', '.join([os.path.basename(f) for f in files])}"

@tool
def process_and_embed(chunk_size: int, chunk_overlap: int) -> str:
    """문서를 분할하여 Vector DB에 저장합니다."""
    files = get_all_pdf_files()
    if not files: return "처리할 문서가 없습니다."
    
    try:
        docs = []
        for file in files: 
            docs.extend(PyPDFLoader(file).load())
        splits = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap).split_documents(docs)
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=CHROMA_DB_DIR)
        return f"[성공] {len(splits)}개의 청크가 DB에 저장되었습니다. test_retrieval로 품질을 검증하세요."
    except Exception as e:
        return f"[에러] 임베딩 실패: {str(e)} -> 청크 사이즈를 조절하세요."

@tool
def test_retrieval(query: str) -> str:
    """구축된 DB를 샘플 쿼리로 자가 검증합니다."""
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        db = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)
        results = db.similarity_search(query, k=1)
        if not results: return "[실패] 검색 결과가 비어있습니다. 설정값을 변경해 다시 시도하세요."
        return f"[성공] 테스트 통과. 추출 샘플: '{results[0].page_content[:100]}...'"
    except Exception as e:
        return f"[에러] 검색 실패: {str(e)}"

@tool
def finish_ingestion(report: str) -> str:
    """문서 파이프라인 구축 완료를 선언합니다."""
    return f"최종 보고: {report}"

# --- [호환성 유지용 래퍼 함수 (sps_main_orchestrator 연동)] ---
def build_vector_db(pdf_path: str = None):
    """sps_main_orchestrator 연동을 위한 벡터 DB 구축 래퍼 함수"""
    files = [pdf_path] if pdf_path and os.path.exists(pdf_path) else get_all_pdf_files()
    if not files: return "처리할 PDF 파일이 없습니다."
    docs = []
    for f in files:
        docs.extend(PyPDFLoader(f).load())
    splits = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200).split_documents(docs)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    Chroma.from_documents(documents=splits, embedding=embeddings, persist_directory=CHROMA_DB_DIR)
    return f"[성공] {len(splits)}개의 청크가 DB에 저장되었습니다."

def query_insurance_rag(question: str) -> str:
    """sps_main_orchestrator 연동을 위한 RAG 질의응답 래퍼 함수"""
    try:
        embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        db = Chroma(persist_directory=CHROMA_DB_DIR, embedding_function=embeddings)
        results = db.similarity_search(question, k=3)
        if not results: return "관련 문서를 찾을 수 없습니다."
        context = "\n\n".join(doc.page_content for doc in results)
        llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0)
        prompt = f"다음 문맥을 바탕으로 질문에 답변하세요.\n\n문맥:\n{context}\n\n질문: {question}\n\n답변:"
        return llm.invoke(prompt).content
    except Exception as e:
        return f"[에러] 질의응답 실패: {str(e)}"
# -------------------------------------------------------------

async def run_rag_agent():
    print("🚀 [RAG 에이전트 가동] 범용 문서 데이터 수집 및 검증 파이프라인 시작")
    
    tools = [scan_directory, process_and_embed, test_retrieval, finish_ingestion]
    llm = ChatGoogleGenerativeAI(model="gemini-3.5-flash", temperature=0).bind_tools(tools)
    
    sys_msg = SystemMessage(content="""당신은 RAG 파이프라인 자율 구축 에이전트입니다.
    순서: 1. scan_directory -> 2. process_and_embed -> 3. test_retrieval -> 4. 완벽하면 finish_ingestion.
    진행 중 에러가 발생하면 도구의 파라미터를 스스로 변경하여 해결하세요.""")

    async def agent_node(state: IngestionState):
        return {"messages": [await llm.ainvoke([sys_msg] + state["messages"])]}
        
    def should_continue(state: IngestionState):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, AIMessage) and last_msg.tool_calls:
            for tc in last_msg.tool_calls:
                if tc["name"] == "finish_ingestion": return END
            return "tools"
        return END

    builder = StateGraph(IngestionState)
    builder.add_node("agent", agent_node)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    builder.add_edge("tools", "agent")
    
    agent = builder.compile()
    state = await agent.ainvoke({"messages": [HumanMessage(content="대상 디렉토리의 모든 문서를 확인하고 Vector DB 구축부터 테스트까지 전부 알아서 진행해줘.")]})
    
    for msg in reversed(state["messages"]):
        if msg.type == "tool" and "최종 보고:" in msg.content:
            return msg.content
    return "파이프라인 구축이 중간에 중단되었습니다."