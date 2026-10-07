# 에이전트의 역할:

# - 보험 고객 문의 이메일 읽기
# - 긴급도와 주제별 분류
# - 보험 약관·상품설명서에서 관련 내용 검색
# - 적절한 답변 초안 작성
# - 복잡한 문제는 담당자에게 인계
# - 필요한 경우 후속 일정 등록

# 처리 예시:

# 1. 단순 보험 보장 문의: "실손의료보험에서 보장되는 항목은 무엇인가요?"
# 2. 보험금 청구 문의: "보험금 청구에 필요한 서류를 알려 주세요."
# 3. 긴급 사고 접수: "사고가 발생했는데 보험금 청구 절차가 어떻게 되나요?"
# 4. 계약 내용 확인: "가입한 보험의 보장기간과 면책사항을 확인해 주세요."
# 5. 복잡한 보험 분쟁: "보험금 지급이 거절된 사유와 재심사 방법을 알려 주세요."

# 이제 워크플로의 구성 요소를 파악했으니 각 노드가 수행해야 하는 작업을 이해해 보겠습니다.
# 이메일 읽기: 이메일 내용을 추출하고 분석합니다.
# 의도 분류: LLM으로 긴급도와 주제를 분류한 다음 적절한 조치로 연결합니다.
# 약관 검색: 보험 약관·상품설명서에서 관련 근거를 검색합니다.
# 보험금 청구 추적: 사고 접수와 보험금 청구 상태를 기록합니다.
# 보험 답변 초안: 약관 근거를 포함한 답변을 생성합니다.
# 담당자 검토: 승인 또는 처리를 위해 담당자에게 인계합니다.
# 답변 발송: 이메일 답변을 발송합니다.

from __future__ import annotations

import logging
import requests
import os
import sys
import hashlib
import smtplib
from email.message import EmailMessage
from urllib.parse import urlparse
from pathlib import Path

# 프로젝트 루트(/data/vm_project)를 import 경로에 추가해 절대경로 직접 실행을 지원합니다.
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from typing import TypedDict, Literal
from langgraph.errors import NodeError
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command, RetryPolicy
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from langchain.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from config import LOG_PATH, MONGO_URI, MONGO_DB, MONGO_TIMEOUT_MS
from common.common_function import ensure_dirs, logger
from common.database import CommonDatabase

try:
    from pymongo import MongoClient
except ImportError:  # MongoDB 저장을 선택적으로 활성화합니다.
    MongoClient = None

ensure_dirs()
EMAIL_LOG_PATH = os.path.join(LOG_PATH, "langgraph_email_rag_agent.log")
if not any(
    isinstance(handler, logging.FileHandler)
    and getattr(handler, "baseFilename", "") == os.path.abspath(EMAIL_LOG_PATH)
    for handler in logger.handlers
):
    _email_handler = logging.FileHandler(EMAIL_LOG_PATH, encoding="utf-8")
    _email_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(_email_handler)

# 이메일 분류 결과의 구조를 정의합니다.
class EmailClassification(TypedDict):
    intent: Literal["question", "bug", "billing", "feature", "complex"]
    urgency: Literal["low", "medium", "high", "critical"]
    topic: str
    summary: str

class EmailAgentState(TypedDict):
    # 원본 이메일 데이터
    email_content: str
    sender_email: str
    email_id: str

    # 분류 결과
    classification: EmailClassification | None

    # 원본 검색/API 결과
    search_results: list[str] | None  # 원본 약관 문서 조각 목록
    tavily_status: str
    customer_history: dict | None  # CRM의 원본 고객 데이터

    # 생성된 콘텐츠
    draft_response: str | None
    messages: list[str] | None

# 노드를 읽고 분류합니다.

gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").split("#", 1)[0].strip() or "gemini-2.5-flash"
llm = ChatGoogleGenerativeAI(model=gemini_model)
tavily_search = TavilySearch(max_results=5) if os.getenv("TAVILY_API_KEY") else None

def _normalize_response_content(content: object) -> str:
    """Gemini content block을 순수 텍스트로 정규화해 signature가 저장되지 않게 합니다."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return "\n".join(
            str(block.get("text", "")).strip()
            for block in content
            if isinstance(block, dict) and block.get("text")
        ).strip()
    return str(content).strip()


def _create_embeddings(texts: list[str]) -> list[list[float]]:
    """Ollama bge-m3에 여러 청크를 한 번에 보내 임베딩 호출을 줄입니다."""
    if not texts:
        return []
    base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3")
    response = requests.post(
        f"{base_url}/api/embed",
        json={"model": model, "input": texts, "keep_alive": "10m"},
        timeout=int(os.getenv("OLLAMA_EMBEDDING_TIMEOUT", "180")),
    )
    response.raise_for_status()
    embeddings = response.json().get("embeddings")
    if not isinstance(embeddings, list) or len(embeddings) != len(texts):
        raise RuntimeError("Ollama 배치 임베딩 응답 수가 입력 청크 수와 다릅니다.")
    logger.info("Ollama 배치 임베딩 완료: model=%s chunks=%s", model, len(embeddings))
    return embeddings


def _save_mongodb_payload(state: EmailAgentState) -> None:
    """환경변수가 있을 때만 보험 RAG 결과를 저장하고 count로 검증합니다."""
    uri = os.getenv("MONGODB_URI") or os.getenv("HEALTH_COMPANION_MONGODB_URI") or MONGO_URI
    if MongoClient is None:
        logger.warning("MongoDB 저장 건너뜀: MONGODB_URI 또는 pymongo 미설정")
        return
    collection_name = os.getenv("MONGODB_COLLECTION", "insurance_policy_terms_payload")
    database_name = os.getenv("MONGODB_DATABASE") or os.getenv("HEALTH_COMPANION_MONGODB_DATABASE", "health_companion_ai")
    document_id = state.get("email_id", "")
    object_id = os.getenv("MONGODB_DOCUMENT_MASTER_ID", "SP_RP_MDM_20261004_00001")
    embedding_text = state.get("email_content", "")
    embedding = _create_embeddings([embedding_text])[0]
    payload = {
        "object_id": object_id,
        "document_id": document_id,
        "audit": {
            "created_dt": datetime.now(timezone.utc),
            "created_by": "CODEX",
            "client_ip": os.getenv("CLIENT_IP", "127.0.0.1"),
            "program_id": "SPS_MONGODB_EMAIL_RAG",
        },
        "payload": {
            "email_content": state.get("email_content", ""),
            "classification": state.get("classification"),
            "search_results": state.get("search_results", []),
            "draft_response": state.get("draft_response", ""),
            "embedding": embedding,
            "embedding_model": os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3"),
        },
    }
    client = MongoClient(uri, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
    try:
        collection = client[database_name][collection_name]
        collection.replace_one({"document_id": document_id}, payload, upsert=True)
        verified = collection.count_documents({"document_id": document_id}) == 1 and collection.count_documents({"document_id": document_id, "payload.embedding": {"$exists": True}}) == 1
        logger.info("MongoDB 저장·검증 %s: collection=%s document_id=%s", "성공" if verified else "실패", collection_name, document_id)
        if not verified:
            raise RuntimeError("MongoDB payload count verification failed")
    finally:
        client.close()


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Split extracted PDF text while preserving configured overlap and the final tail."""
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap must be smaller than chunk_size.")
    if not text:
        return []
    step = chunk_size - overlap
    return [text[pos:pos + chunk_size] for pos in range(0, len(text), step)]


def _create_embeddings_in_batches(texts: list[str]) -> list[list[float]]:
    """Embed all supplied chunks in bounded batches and fail if any chunk is omitted."""
    batch_size = int(os.getenv("OLLAMA_EMBEDDING_BATCH_SIZE", "16"))
    if batch_size <= 0:
        raise ValueError("OLLAMA_EMBEDDING_BATCH_SIZE must be greater than zero.")
    embeddings: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start:start + batch_size]
        batch_embeddings = _create_embeddings(batch)
        if len(batch_embeddings) != len(batch):
            raise RuntimeError(
                f"Ollama returned {len(batch_embeddings)} embeddings for {len(batch)} input chunks."
            )
        embeddings.extend(batch_embeddings)
    return embeddings


def ingest_insurance_pdfs(state: EmailAgentState) -> dict:
    """Read every insurance PDF, embed every chunk, and verify each source file's saved rows."""
    if MongoClient is None or PdfReader is None:
        raise RuntimeError("PDF ingestion requires pymongo and pypdf; no input is silently skipped.")

    pdf_folder = Path(os.getenv("AGENT_DOCUMENT_DIR", str(PROJECT_ROOT / "FastAPI" / "LangGraph" / "insurance_docs")))
    pdf_paths = sorted(path for path in pdf_folder.rglob("*") if path.is_file() and path.suffix.lower() == ".pdf")
    if not pdf_paths:
        raise FileNotFoundError(f"보험 약관 PDF가 없습니다: {pdf_folder}")

    # Extract all PDFs before database writes so an unreadable source cannot produce a partial first pass.
    source_documents: list[tuple[str, str, list[str]]] = []
    for pdf_path in pdf_paths:
        source_name = pdf_path.relative_to(pdf_folder).as_posix()
        extracted_text = "\\n".join((page.extract_text() or "") for page in PdfReader(str(pdf_path)).pages)
        if not extracted_text.strip():
            raise RuntimeError(f"PDF에서 텍스트를 추출하지 못했습니다: {source_name}")
        chunks = _chunk_text(extracted_text)
        source_documents.append((source_name, extracted_text, chunks))
        logger.info("PDF 텍스트 추출 완료: file=%s chars=%s chunks=%s", source_name, len(extracted_text), len(chunks))

    uri = os.getenv("MONGODB_URI") or os.getenv("HEALTH_COMPANION_MONGODB_URI") or MONGO_URI
    collection_name = os.getenv("MONGODB_COLLECTION", "insurance_policy_terms_payload")
    database_name = os.getenv("MONGODB_DATABASE", "health_companion_ai")
    client = MongoClient(uri, serverSelectionTimeoutMS=MONGO_TIMEOUT_MS)
    source_chunk_counts: dict[str, int] = {}
    try:
        collection = client[database_name][collection_name]
        for source_name, _extracted_text, chunks in source_documents:
            # Bounded batch calls process every chunk while avoiding one oversized request per large PDF.
            embeddings = _create_embeddings_in_batches(chunks)
            expected_document_ids: list[str] = []
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
                # Relative source path and chunk number keep IDs stable and avoid same-basename collisions.
                source_digest = hashlib.sha256(source_name.encode("utf-8")).hexdigest()[:12]
                document_id = f"{Path(source_name).stem}:{source_digest}:{index:05d}"
                expected_document_ids.append(document_id)
                document = {
                    "object_id": os.getenv("MONGODB_DOCUMENT_MASTER_ID", "SP_RP_MDM_20261004_00001"),
                    "mongodb_database_id": os.getenv("MONGODB_DATABASE_ID", "SP_RP_MDB_2026_00001"),
                    "mongodb_collection_id": os.getenv("MONGODB_COLLECTION_ID", "SP_RP_MCO_202608_00001"),
                    "mongodb_document_master_id": os.getenv("MONGODB_DOCUMENT_MASTER_ID", "SP_RP_MCM_20260801_00001"),
                    "document_id": document_id,
                    "source_file": source_name,
                    "chunk_index": index,
                    "chunk_size": len(chunk),
                    "payload": {
                        "normalized_text": chunk,
                        "embedding": embedding,
                        "embedding_model": os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3"),
                    },
                    "audit": {
                        "created_dt": datetime.now(timezone.utc),
                        "created_by": "CODEX",
                        "client_ip": os.getenv("CLIENT_IP", "127.0.0.1"),
                        "program_id": "SPS_MONGODB_DOCUMENT_PDF",
                    },
                }
                collection.update_one({"document_id": document_id}, {"$set": document}, upsert=True)

            # Verify this PDF's exact IDs and embeddings, independent of unrelated collection rows.
            verified_count = collection.count_documents({
                "document_id": {"$in": expected_document_ids},
                "source_file": source_name,
                "payload.embedding": {"$exists": True},
            })
            if verified_count != len(expected_document_ids):
                raise RuntimeError(
                    f"PDF 저장 검증 실패: file={source_name} expected={len(expected_document_ids)} actual={verified_count}"
                )
            source_chunk_counts[source_name] = verified_count
            logger.info(
                "PDF별 저장·검증 성공: file=%s chunks=%s collection=%s",
                source_name, verified_count, collection_name,
            )
    finally:
        client.close()

    return {
        "pdf_file_count": len(source_documents),
        "pdf_chunk_count": sum(source_chunk_counts.values()),
        "source_chunk_counts": source_chunk_counts,
    }


def read_email(state: EmailAgentState) -> dict:
    """이메일 내용을 추출하고 분석합니다."""
    # 운영 환경에서는 이메일 서비스에 연결합니다.
    return {
        "messages": [HumanMessage(content=f"Processing email: {state['email_content']}")]
    }

def classify_intent(state: EmailAgentState) -> Command[Literal["search_documentation", "human_review", "draft_response", "bug_tracking"]]:
    """LLM으로 이메일 의도와 긴급도를 분류한 뒤 다음 단계로 연결합니다."""

    # EmailClassification 형식의 구조화된 결과를 반환하도록 설정합니다.
    structured_llm = llm.with_structured_output(EmailClassification)

    # 프롬프트는 상태에 저장하지 않고 실행 시 구성합니다.
    classification_prompt = f"""
    다음 보험 고객 문의를 분석하고 분류하세요:

    이메일: {state['email_content']}
    발신자: {state['sender_email']}

    보험 문의 의도, 긴급도, 보험종목, 관련 담보, 요약을 포함해 분류 결과를 제공하세요.
    """

    # 구조화된 응답을 딕셔너리로 받습니다.
    classification = structured_llm.invoke(classification_prompt)

    # 분류 결과에 따라 다음 노드를 결정합니다.
    if classification['intent'] == 'billing' or classification['urgency'] == 'critical':
        goto = "human_review"
    elif classification['intent'] in ['question', 'feature']:
        goto = "search_router"
    elif classification['intent'] == 'bug':
        goto = "bug_tracking"
    else:
        goto = "draft_response"

    # 분류 결과를 하나의 딕셔너리로 상태에 저장합니다.
    return Command(
        update={"classification": classification},
        goto=goto
    )


# 검색 및 추적 노드

def search_documentation(state: EmailAgentState) -> dict:
    """보험 약관·상품설명서에서 관련 정보를 검색합니다."""

    # 분류 결과로 검색 질의를 구성합니다.
    classification = state.get('classification', {})
    query = f"{classification.get('intent', '')} {classification.get('topic', '')}"
    tavily_status = "disabled"

    try:
        # 실제 검색 로직을 이 위치에 연결합니다.
        # 형식화하지 않은 원본 검색 결과를 저장합니다.
        search_results = [
            "실손의료보험 약관의 보장 대상 및 지급 제한",
            "보험금 청구에 필요한 진료비 영수증과 진료기록",
            "면책사항·보장 제외 항목은 약관 원문을 확인해야 함"
        ]
        if tavily_search:
            web_result = tavily_search.invoke(query)
            tavily_status = "success"
            if isinstance(web_result, dict):
                allowed = {
                    d.strip().lower()
                    for d in os.getenv(
                        "TAVILY_ALLOWED_DOMAINS",
                        "fss.or.kr,e-insmarket.or.kr,kidi.or.kr"
                    ).split(",")
                    if d.strip()
                }
                web_items = web_result.get("results", [])
                for item in web_items:
                    url = item.get("url", "")
                    host = urlparse(url).netloc.lower().split(":")[0]
                    if host in allowed or any(host.endswith("." + domain) for domain in allowed):
                        content = item.get("content", "").strip()
                        if content:
                            search_results.append(f"[출처: {url}] {content[:2000]}")
    except Exception as e:
        logger.exception("문서 검색 실패")
        tavily_status = "failed"
        # 복구 가능한 검색 오류는 오류를 저장하고 계속 진행합니다.
        search_results = [f"검색을 일시적으로 사용할 수 없습니다: {str(e)}"]

    return {"search_results": search_results, "tavily_status": tavily_status}

def search_router(state: EmailAgentState) -> dict:
    """웹 검색, 내부 RAG, 종료 중 하나를 선택합니다."""
    text = state.get("email_content", "").lower()
    web_terms = ("웹", "검색", "최신", "뉴스", "외부", "latest", "current", "news", "web")
    rag_terms = ("보험", "약관", "보장", "청구", "계약", "면책", "실손", "policy", "coverage")
    mode = "tavily" if any(term in text for term in web_terms) else "rag_search" if any(term in text for term in rag_terms) else "end"
    logger.info("검색 경로 선택: mode=%s", mode)
    return {"search_mode": mode}

def rag_search_node(state: EmailAgentState) -> dict:
    """내부 보험 약관 RAG 검색 결과를 반환합니다."""
    return {"search_results": [
        "실손의료보험 약관의 보장 대상 및 지급 제한",
        "보험금 청구에 필요한 진료비 영수증과 진료기록",
        "면책사항·보장 제외 항목은 약관 원문을 확인해야 함",
    ], "tavily_status": "disabled"}

def tavily_search_node(state: EmailAgentState) -> dict:
    """Tavily 웹 검색만 수행합니다."""
    return search_documentation(state)

def route_after_search(state: EmailAgentState) -> Literal["tavily_search", "rag_search", "end"]:
    return state.get("search_mode", "end")

def bug_tracking(state: EmailAgentState) -> Command[Literal["draft_response"]]:
    """보험금 청구 추적 건을 생성하거나 갱신합니다."""

    # 버그 추적 시스템에 티켓을 생성합니다.
    ticket_id = "BUG-12345"  # 운영 환경에서는 API로 생성합니다.

    return Command(
        update={
            "search_results": [f"보험금 청구 추적 건 {ticket_id}가 생성되었습니다."],
            "current_step": "bug_tracked"
        },
        goto="draft_response"
    )

# 응답 노드

def draft_response(state: EmailAgentState) -> Command[Literal["human_review", "send_reply"]]:
    """약관 문맥으로 답변을 생성하고 검토 필요 여부에 따라 연결합니다."""

    classification = state.get('classification', {})

    # 원본 상태 데이터로 문맥을 실행 시 구성합니다.
    context_sections = []

    if state.get('search_results'):
        # 프롬프트에 넣을 검색 결과를 구성합니다.
        formatted_docs = "\n".join([f"- {doc}" for doc in state['search_results']])
        context_sections.append(f"관련 약관·상품 문서:\n{formatted_docs}")

    if state.get('customer_history'):
        # 프롬프트에 넣을 고객 데이터를 구성합니다.
        context_sections.append(f"계약자 등급: {state['customer_history'].get('tier', 'standard')}")

    # 구성한 문맥을 포함해 답변 프롬프트를 만듭니다.
    draft_prompt = f"""
    다음 보험 고객 문의에 대한 답변을 작성하세요:
    {state['email_content']}

    문의 의도: {classification.get('intent', 'unknown')}
    긴급도: {classification.get('urgency', 'medium')}

    {chr(10).join(context_sections)}

    보험 답변 작성 지침:
    - 전문적이고 이해하기 쉽게 작성하세요.
    - 문의한 보장·청구 사항을 구체적으로 다루세요.
    - 관련 약관의 근거를 사용하되 약관에 없는 내용은 단정하지 마세요.
    """

    response = llm.invoke(draft_prompt)

    # 긴급도와 의도에 따라 담당자 검토 필요 여부를 결정합니다.
    needs_review = (
        classification.get('urgency') in ['high', 'critical'] or
        classification.get('intent') == 'complex'
    )

    # 다음 노드로 연결합니다.
    goto = "human_review" if needs_review else "send_reply"

    return Command(
        update={"draft_response": _normalize_response_content(response.content)},  # signature를 제외한 텍스트만 저장합니다.
        goto=goto
    )

def human_review(state: EmailAgentState) -> Command[Literal["send_reply", END]]:
    """Pause for human review using interrupt and route based on decision"""

    classification = state.get('classification', {})

    # interrupt()를 먼저 호출해야 재개 시 앞의 코드가 다시 실행되지 않습니다.
    human_decision = interrupt({
        "email_id": state.get('email_id',''),
        "original_email": state.get('email_content',''),
        "draft_response": state.get('draft_response',''),
        "urgency": classification.get('urgency'),
        "intent": classification.get('intent'),
        "action": "답변을 검토하고 승인하거나 수정해 주세요."
    })

    # 담당자의 결정을 처리합니다.
    if human_decision.get("approved"):
        return Command(
            update={"draft_response": human_decision.get("edited_response", state.get('draft_response',''))},
            goto="send_reply"
        )
    else:
        # 거부하면 담당자가 직접 처리합니다.
        return Command(update={}, goto=END)

def send_reply(state: EmailAgentState) -> dict:
    """보험 문의 답변을 발송합니다."""
    _save_mongodb_payload(state)
    # SMTP 비밀값은 소스에 저장하지 않고 .env에서 주입합니다.
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("EMAIL_FROM", smtp_username)
    # 수신 주소를 지정하지 않으면 실수로 실제 메일이 발송되지 않도록 중단합니다.
    recipient = os.getenv("EMAIL_TO")
    if not smtp_username or not smtp_password or not sender or not recipient:
        logger.error("이메일 발송 실패: SMTP_USERNAME/SMTP_PASSWORD/EMAIL_FROM 설정 누락")
        raise RuntimeError("SMTP_USERNAME, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO 설정이 필요합니다.")

    message = EmailMessage()
    message["Subject"] = "실손의료보험 문의 답변"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(state.get("draft_response", ""))

    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(message)
        logger.info("이메일 발송 성공: recipient=%s", recipient)
        print(f"Email sent successfully: {recipient}")
    except Exception:
        logger.exception("이메일 발송 실패: recipient=%s", recipient)
        raise
    return {}

# 그래프 컴파일 코드

# 그래프를 생성합니다.
workflow = StateGraph(EmailAgentState)

# 오류 처리를 포함해 노드를 추가합니다.
workflow.add_node("ingest_insurance_pdfs", ingest_insurance_pdfs)
workflow.add_node("read_email", read_email)
workflow.add_node("classify_intent", classify_intent)
workflow.add_node("search_router", search_router)
workflow.add_node("rag_search", rag_search_node)
workflow.add_node("tavily_search", tavily_search_node)

# 일시적 오류가 발생할 수 있는 노드에 재시도 정책을 추가합니다.
workflow.add_node(
    "search_documentation",
    search_documentation,
    retry_policy=RetryPolicy(max_attempts=3)
)
workflow.add_node("bug_tracking", bug_tracking)
workflow.add_node("draft_response", draft_response)
workflow.add_node("human_review", human_review)
workflow.add_node("send_reply", send_reply)

# 필수 엣지만 추가합니다.
workflow.add_edge(START, "ingest_insurance_pdfs")
workflow.add_edge("ingest_insurance_pdfs", "read_email")
workflow.add_conditional_edges("search_router", route_after_search, {"tavily_search": "tavily_search", "rag_search": "rag_search", "end": "draft_response"})
workflow.add_edge("tavily_search", "draft_response")
workflow.add_edge("rag_search", "draft_response")
workflow.add_edge("read_email", "classify_intent")
workflow.add_edge("send_reply", END)

# Compile with checkpointer for persistence, in case run graph with Local_Server --> Please compile without checkpointer
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)


if __name__ == "__main__":
    # 직접 실행 시에도 동일한 그래프를 호출할 수 있도록 기본 입력을 구성합니다.
    initial_state: EmailAgentState = {
        "email_content": "실손의료보험의 최근 리 발목이 부러졌고, 웹으로 산재에서도 보장 및 범위를 알려 주세요.",
        "sender_email": "demo@example.com",
        "email_id": "demo-email-001",
        "classification": None,
        "search_results": None,
        "customer_history": None,
        "draft_response": None,
        "messages": None,
    }
    result = app.invoke(
        initial_state,
        config={"configurable": {"thread_id": "demo-email-001"}},
    )
    print(f"Email RAG result: {result}")
