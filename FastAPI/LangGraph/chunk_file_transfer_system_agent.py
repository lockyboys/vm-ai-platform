import os
import shutil
import zipfile
import threading
import time
import requests
from typing import TypedDict
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.responses import FileResponse
from langgraph.graph import StateGraph, END
import uvicorn

# ==========================================
# 1. FastAPI 서버 파트 (파일 수신 및 송출)
# ==========================================
app = FastAPI(title="Chunk & Folder Bi-directional Transfer Server", version="10.0.0")

BASE_STORAGE = "./downloaded_docs"
os.makedirs(BASE_STORAGE, exist_ok=True)

@app.get("/files")
def server_list_files(subfolder: str = ""):
    target_dir = os.path.join(BASE_STORAGE, subfolder) if subfolder else BASE_STORAGE
    if not os.path.exists(target_dir):
        return {"files": [], "path": target_dir}
    return {"files": os.listdir(target_dir), "path": target_dir}

@app.post("/upload_chunk/")
async def server_upload_chunk(
    file: UploadFile = File(...),
    filename: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    subfolder: str = Form(""),
    is_folder: bool = Form(False)
):
    target_dir = os.path.join(BASE_STORAGE, subfolder) if subfolder else BASE_STORAGE
    os.makedirs(target_dir, exist_ok=True)
    
    temp_dir = os.path.join(target_dir, "temp_chunks")
    os.makedirs(temp_dir, exist_ok=True)
    
    chunk_path = os.path.join(temp_dir, f"{filename}.part_{chunk_index}")
    with open(chunk_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    received_chunks = [f for f in os.listdir(temp_dir) if f.startswith(f"{filename}.part_")]
    if len(received_chunks) == total_chunks:
        final_path = os.path.join(target_dir, filename)
        with open(final_path, "wb") as final_file:
            for i in range(total_chunks):
                part_path = os.path.join(temp_dir, f"{filename}.part_{i}")
                with open(part_path, "rb") as part_file:
                    final_file.write(part_file.read())
                os.remove(part_path)
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        if is_folder and final_path.endswith(".zip"):
            extract_path = final_path[:-4]
            os.makedirs(extract_path, exist_ok=True)
            with zipfile.ZipFile(final_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            os.remove(final_path)
            return {"filename": filename, "status": "folder_extracted", "saved_to": extract_path}
            
        return {"filename": filename, "status": "file_completed", "saved_to": final_path}
    
    return {"filename": filename, "chunk_index": chunk_index, "status": "chunk_received"}

@app.get("/download_item")
def server_download_item(name: str, subfolder: str = "", is_folder: bool = False):
    target_dir = os.path.join(BASE_STORAGE, subfolder) if subfolder else BASE_STORAGE
    target_path = os.path.join(target_dir, name)
    
    if is_folder and os.path.isdir(target_path):
        zip_filename = f"{name}.zip"
        zip_path = os.path.join(target_dir, zip_filename)
        shutil.make_archive(zip_path[:-4], 'zip', target_path)
        return FileResponse(zip_path, media_type='application/zip', filename=zip_filename)
    elif os.path.isfile(target_path):
        return FileResponse(target_path, media_type='application/octet-stream', filename=name)
        
    raise HTTPException(status_code=404, detail="File or Folder not found")


# ==========================================
# 2. 로컬 테스트용 클라이언트 도구
# ==========================================
SERVER_URL = "http://127.0.0.1:8000"
CHUNK_SIZE = 1024 * 1024  # 1MB 청크

def tool_upload_item(local_path: str, server_subfolder: str = "", is_folder: bool = False) -> str:
    upload_target = local_path
    if is_folder:
        if not os.path.isdir(local_path):
            return f"[오류] 로컬 폴더 없음: {local_path}"
        zip_path = shutil.make_archive(local_path, 'zip', local_path)
        upload_target = zip_path
        filename = os.path.basename(zip_path)
    else:
        if not os.path.isfile(local_path):
            return f"[오류] 로컬 파일 없음: {local_path}"
        filename = os.path.basename(local_path)

    file_size = os.path.getsize(upload_target)
    total_chunks = (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE

    try:
        with open(upload_target, "rb") as f:
            for idx in range(total_chunks):
                chunk_data = f.read(CHUNK_SIZE)
                files = {"file": (filename, chunk_data)}
                data = {
                    "filename": filename,
                    "chunk_index": idx,
                    "total_chunks": total_chunks,
                    "subfolder": server_subfolder,
                    "is_folder": is_folder
                }
                res = requests.post(f"{SERVER_URL}/upload_chunk/", files=files, data=data)
                if res.status_code != 200:
                    return f"[오류] 청크 {idx} 전송 실패: {res.text}"
        
        if is_folder and os.path.exists(upload_target):
            os.remove(upload_target)
            
        return f"[업로드 성공] 대상: {local_path} -> 서버 루트"
    except Exception as e:
        return f"[오류] 업로드 예외: {str(e)}"

def tool_download_item(name: str, server_subfolder: str = "", save_dir: str = "./downloads", is_folder: bool = False) -> str:
    os.makedirs(save_dir, exist_ok=True)
    try:
        res = requests.get(
            f"{SERVER_URL}/download_item", 
            params={"name": name, "subfolder": server_subfolder, "is_folder": is_folder}, 
            stream=True
        )
        if res.status_code == 200:
            if is_folder:
                zip_target = os.path.join(save_dir, f"{name}.zip")
                with open(zip_target, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                extract_to = os.path.join(save_dir, name)
                os.makedirs(extract_to, exist_ok=True)
                with zipfile.ZipFile(zip_target, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                os.remove(zip_target)
                return f"[폴더 다운로드 성공] 복원 경로: {os.path.abspath(extract_to)}"
            else:
                target = os.path.join(save_dir, name)
                with open(target, "wb") as f:
                    for chunk in res.iter_content(chunk_size=8192):
                        f.write(chunk)
                return f"[파일 다운로드 성공] 저장 경로: {os.path.abspath(target)}"
                
        return f"[오류] 다운로드 실패: {res.text}"
    except Exception as e:
        return f"[오류] 다운로드 예외: {str(e)}"

def tool_list_files(subfolder: str = "") -> str:
    try:
        res = requests.get(f"{SERVER_URL}/files", params={"subfolder": subfolder})
        if res.status_code == 200:
            data = res.json()
            return f"[목록 조회 성공] 서버 경로: {data.get('path')} \n- 항목: {data.get('files', [])}"
        return f"[오류] 목록 조회 실패: {res.text}"
    except Exception as e:
        return f"[오류] 서버 연결 예외: {str(e)}"


# ==========================================
# 3. LangGraph 에이전트 워크플로우
# ==========================================
class AgentState(TypedDict):
    command: str
    intent: str
    target_name: str
    server_folder: str
    client_folder: str
    is_folder: bool
    result: str

def intent_analyzer_node(state: AgentState) -> AgentState:
    if not state.get("server_folder"):
        state["server_folder"] = ""
    if not state.get("client_folder"):
        state["client_folder"] = "./downloads"
    return state

def execution_node(state: AgentState) -> AgentState:
    intent = state["intent"].lower()
    if intent == "upload":
        state["result"] = tool_upload_item(
            local_path=state["target_name"],
            server_subfolder=state["server_folder"],
            is_folder=state["is_folder"]
        )
    elif intent == "download":
        state["result"] = tool_download_item(
            name=state["target_name"], 
            server_subfolder=state["server_folder"], 
            save_dir=state["client_folder"], 
            is_folder=state["is_folder"]
        )
    elif intent == "list":
        state["result"] = tool_list_files(subfolder=state["server_folder"])
    else:
        state["result"] = "[오류] 지원하지 않는 작업입니다."
    return state

workflow = StateGraph(AgentState)
workflow.add_node("analyzer", intent_analyzer_node)
workflow.add_node("executor", execution_node)
workflow.set_entry_point("analyzer")
workflow.add_edge("analyzer", "executor")
workflow.add_edge("executor", END)
agent_app = workflow.compile()


# ==========================================
# 4. 실행 및 테스트 (Main)
# ==========================================
def run_server():
    # 💡 윈도우 PC(외부)에서 접속 가능하도록 host="0.0.0.0" 적용 완료
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

if __name__ == "__main__":
    os.system("fuser -k 8000/tcp > /dev/null 2>&1")
    time.sleep(0.5)

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("🚀 청크 기반 양방향 전송 서버가 백그라운드에서 실행되었습니다. (포트: 8000)")
    time.sleep(1.0)

    # 테스트용 파일 생성
    local_test_dir = "./www.axa.co.kr"
    os.makedirs(local_test_dir, exist_ok=True)
    with open(os.path.join(local_test_dir, "doc1.txt"), "w", encoding="utf-8") as f:
        f.write("폴더 내 첫 번째 문서 내용입니다.")

    print("\n--- [시나리오 1] 업로드 테스트 ---")
    res1 = agent_app.invoke({
        "command": f"업로드 {local_test_dir}",
        "intent": "upload", 
        "target_name": local_test_dir,
        "is_folder": True, 
        "result": ""
    })
    print(res1["result"])

    print("\n--- [시나리오 2] 목록 조회 테스트 ---")
    res2 = agent_app.invoke({
        "command": "목록",
        "intent": "list", 
        "result": ""
    })
    print(res2["result"])

    print("\n--- [시나리오 3] 다운로드 테스트 ---")
    res3 = agent_app.invoke({
        "command": "다운로드 www.axa.co.kr",
        "intent": "download",
        "target_name": "www.axa.co.kr",
        "client_folder": "./client_downloads",
        "is_folder": True,
        "result": ""
    })
    print(res3["result"])

    if os.path.exists(local_test_dir):
        shutil.rmtree(local_test_dir)