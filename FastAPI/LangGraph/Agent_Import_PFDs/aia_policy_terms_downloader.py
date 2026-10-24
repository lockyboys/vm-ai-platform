"""AIA 공개 공시실 약관 전량 수집기.

요청 범위: 개인/단체/특약, 판매중/판매중지, 모든 공시 개정 이력의 약관
첨부 5/6. 상품요약서/사업방법서/안내장(다른 첨부)은 제외한다.
review_python_source 검토 대상: 목록 누락, CP949 디코딩, 재개 시 손상 검증,
PDF 위장 HTML, 오류 전파, 중복 실행, 안전한 경로와 부분파일 처리.
검토 도구는 실행하지 않는다. 실제 실행은 별도 승인된 MCP Python 도구 사용.
입력 JSON mode=self_test|plan|start|status. 기본 plan으로 PDF는 받지 않는다.
DB 저장 요청은 없으므로 DB 연결/변경 없이 root config와 공통 문자열 검증만 사용.
"""
from __future__ import annotations
import concurrent.futures
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = "https://mypage.aia.co.kr/AIAHomepage"
CATALOG = BASE + "/disclosure/our-products/search/DC1033_1.json"
KST = timezone(timedelta(hours=9))
HEADERS = {"User-Agent": "SPS-AIA-public-policy-downloader/1.0",
           "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
           "Referer": BASE + "/disclosure/product.do"}

def now():
    """모든 실행 증빙 시각은 한국시간으로 기록한다."""
    return datetime.now(KST).isoformat(timespec="seconds")

def atomic_json(path, value):
    """단일 작성자 아래 JSON을 교체하여 상태 파일의 부분 쓰기를 방지한다."""
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.{time.time_ns()}.tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)

def decode_catalog(raw):
    """사이트의 CP949 응답을 UTF-8 replacement 없이 원문 보존해 해석한다."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("cp949")
    data = json.loads(text)
    if data.get("rspCd") != "0000" or not isinstance(data.get("data"), list):
        raise ValueError("AIA catalog error or invalid data list")
    if not data["data"]:
        raise ValueError("Empty catalog cannot prove collection completeness")
    return data["data"]

def targets_from_rows(rows):
    """공식 화면에서 약관에 매핑된 첨부 5/6만 추출하고 원본 행 연결을 유지한다."""
    targets = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid catalog row")
        for slot in (5, 6):
            server = row.get(f"pro_svr_attach{slot}")
            if not server:
                continue
            if not isinstance(server, str) or not re.fullmatch(r"[A-Za-z0-9_.-]+\.pdf", server, re.I) or server.startswith("."):
                raise ValueError("Unsafe or unsupported server PDF filename")
            user = row.get(f"pro_usr_attach{slot}") or server
            if not isinstance(user, str):
                raise ValueError("Invalid original PDF name")
            target = targets.setdefault(server, {"server_file": server, "original_name": user, "references": []})
            target["references"].append({k: row.get(k) for k in (
                "pro_parent_seq", "pro_sub_seq", "pro_title", "pro_status",
                "pro_kind", "pro_start_date", "pro_end_date")})
    if not targets:
        raise ValueError("No policy PDF targets")
    return list(targets.values())

def inspect_pdf(path):
    """헤더·EOF·크기 및 SHA256을 확인한다. 의미적 약관 내용 판독 검증은 아니다."""
    size = path.stat().st_size
    with path.open("rb") as stream:
        head = stream.read(1024)
        stream.seek(max(0, size - 4096))
        tail = stream.read()
    if not head.startswith(b"%PDF-") or b"%%EOF" not in tail:
        raise ValueError("Not a complete PDF (header/EOF validation)")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"bytes": size, "sha256": digest.hexdigest()}

def fetch_catalog():
    """공개 검색 화면과 같은 전체 필터 POST를 사용한다. 접근 제한은 우회하지 않는다."""
    request = urllib.request.Request(CATALOG, data=b"pro_status=&pro_kind=&pro_title=", headers=HEADERS)
    with urllib.request.urlopen(request, timeout=45) as response:
        rows = decode_catalog(response.read())
    # 누락 없는 전체 수집 판정을 위해 판매 상태 두 종류가 목록에 있어야 한다.
    if not {"0", "1"}.issubset({str(x.get("pro_status")) for x in rows}):
        raise ValueError("Catalog does not include both sale statuses")
    return rows

def one_pdf(target, pdf_dir):
    """기존 파일은 검증 후 재사용하며 새 파일만 .part 작성 후 원자적으로 설치한다."""
    name = target["server_file"]
    path = pdf_dir / name
    if path.exists():
        return {"server_file": name, "status": "existing_verified", **inspect_pdf(path)}
    query = urllib.parse.urlencode({"serverFileNm": name, "usrFileNm": target["original_name"]})
    url = BASE + "/disclosure/download.do?" + query
    part = pdf_dir / (name + ".part")
    for attempt in range(3):
        try:
            # 사용자 디스크 고갈을 막고, 인증/차단 응답은 다운로드 성공으로 세지 않는다.
            if shutil.disk_usage(pdf_dir).free < 1024 ** 3:
                raise OSError("Less than 1 GiB free disk space")
            request = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(request, timeout=30) as response, part.open("wb") as dest:
                if urllib.parse.urlsplit(response.url).hostname not in {"mypage.aia.co.kr", "www.aia.co.kr"}:
                    raise ValueError("Unexpected download redirect host")
                total = 0
                while True:
                    chunk = response.read(128 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > 512 * 1024 ** 2:
                        raise ValueError("PDF exceeds 512 MiB limit")
                    dest.write(chunk)
            info = inspect_pdf(part)
            os.replace(part, path)
            time.sleep(0.2)
            return {"server_file": name, "status": "downloaded_verified", **info}
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            part.unlink(missing_ok=True)
            if isinstance(error, urllib.error.HTTPError) and error.code not in (429, 500, 502, 503, 504):
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
        except Exception:
            part.unlink(missing_ok=True)
            raise
    raise RuntimeError("Unexpected retry exhaustion")

def worker(out):
    """프로세스 락 하나와 두 다운로드 스레드로 동작하며 매 파일 결과를 지속 기록한다."""
    with (out / "worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
        targets = plan["targets"]
        results = []
        state = {"state": "RUNNING", "started_kst": now(), "pid": os.getpid(),
                 "expected_unique_pdfs": len(targets), "finished": 0, "success": 0, "failed": 0}
        atomic_json(out / "status.json", state)
        pdf_dir = out / "pdf"
        pdf_dir.mkdir(exist_ok=True)
        with (out / "manifest.jsonl").open("a", encoding="utf-8") as manifest:
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                futures = {pool.submit(one_pdf, target, pdf_dir): target for target in targets}
                for future in concurrent.futures.as_completed(futures):
                    target = futures[future]
                    try:
                        result = future.result()
                        state["success"] += 1
                    except Exception as error:
                        result = {"server_file": target["server_file"], "status": "failed",
                                  "error_type": type(error).__name__, "error": str(error)[:300]}
                        state["failed"] += 1
                    result["checked_kst"] = now()
                    manifest.write(json.dumps(result, ensure_ascii=False) + "\n")
                    manifest.flush()
                    results.append(result)
                    state["finished"] += 1
                    state["updated_kst"] = now()
                    atomic_json(out / "status.json", state)
        # 발견 목록 기준 완료만 판정한다. 공개되지 않은 보험 약관의 존재까지 증명하지 않는다.
        state["state"] = "COMPLETE" if state["failed"] == 0 and state["success"] == len(targets) else "PARTIAL"
        state["ended_kst"] = now()
        state["scope"] = "All terms attachments 5/6 in saved official catalog snapshot"
        atomic_json(out / "failures.json", [x for x in results if x["status"] == "failed"])
        atomic_json(out / "status.json", state)

def self_test():
    """실제 장애 입력을 포함한 회귀 검증. 네트워크/DB/PDF 수집은 수행하지 않는다."""
    import tempfile
    class Checks(unittest.TestCase):
        def test_duplicate_worker_preserves_status(self):
            from unittest import mock
            with (
                mock.patch.object(sys, "argv", [__file__, "--worker", "/unused"]),
                mock.patch(__name__ + ".worker", side_effect=BlockingIOError),
                mock.patch(__name__ + ".atomic_json") as save,
            ):
                main()
                save.assert_not_called()
        def test_empty_catalog(self):
            with self.assertRaises(ValueError):
                decode_catalog(b'{"rspCd":"0000","data":[]}')
        def test_api_failure(self):
            with self.assertRaises(ValueError):
                decode_catalog(b'{"rspCd":"9999","data":[]}')
        def test_cp949(self):
            raw = json.dumps({"rspCd":"0000","data":[{"pro_title":"약관"}]}, ensure_ascii=False).encode("cp949")
            self.assertEqual(decode_catalog(raw)[0]["pro_title"], "약관")
        def test_terms_and_dedup(self):
            rows = [{"pro_svr_attach1":"summary.pdf","pro_svr_attach5":"term.pdf","pro_svr_attach6":"term.pdf"}]
            targets = targets_from_rows(rows)
            self.assertEqual(len(targets), 1)
            self.assertEqual(len(targets[0]["references"]), 2)
        def test_unsafe_name(self):
            with self.assertRaises(ValueError):
                targets_from_rows([{"pro_svr_attach5":"../term.pdf"}])
        def test_html_and_truncated(self):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "bad.pdf"
                for content in (b"<html>blocked</html>", b"%PDF-1.7 truncated"):
                    path.write_bytes(content)
                    with self.assertRaises(ValueError):
                        inspect_pdf(path)
        def test_valid_pdf_hash(self):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "ok.pdf"
                data = b"%PDF-1.4\nmock fixture\n%%EOF\n"
                path.write_bytes(data)
                self.assertEqual(inspect_pdf(path)["sha256"], hashlib.sha256(data).hexdigest())
    result = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(Checks))
    if not result.wasSuccessful():
        raise SystemExit(1)
    return {"tests": result.testsRun, "passed": result.wasSuccessful()}

def main():
    """검토와 수집을 구분한다. JSON stdin 제어 외 임의 코드/명령은 받지 않는다."""
    if len(sys.argv) == 3 and sys.argv[1] == "--worker":
        out = Path(sys.argv[2])
        try:
            worker(out)
        except BlockingIOError:
            # 이미 실행 중인 워커의 상태를 덮어쓰지 않고 중복 워커만 종료한다.
            return
        except Exception as error:
            atomic_json(out / "status.json", {"state":"FAILED","error_type":type(error).__name__,
                                            "error":str(error)[:300],"ended_kst":now()})
            raise
        return
    options = json.loads(sys.stdin.read() or "{}")
    mode = options.get("mode", "plan")
    if mode == "self_test":
        print(json.dumps(self_test()))
        return
    if mode not in {"plan", "start", "status"}:
        raise ValueError("Unsupported mode")
    import config
    from common.common_function import normalize_required_text
    base_output = Path(normalize_required_text(str(config.OUTPUT_PATH), "OUTPUT_PATH")).resolve()
    out = base_output / "insurance_docs" / "AIA"
    out.mkdir(parents=True, exist_ok=True)
    if mode == "status":
        path = out / "status.json"
        print(json.dumps({"output_dir":str(out), "status":json.loads(path.read_text(encoding="utf-8")) if path.exists() else "NOT_STARTED"}, ensure_ascii=False))
        return
    if mode == "plan":
        rows = fetch_catalog()
        targets = targets_from_rows(rows)
        stamp = datetime.now(KST).strftime("%Y%m%d_%H%M%S")
        plan = {"planned_kst":now(), "catalog_url":CATALOG, "catalog_rows":len(rows),
                "attachment_references":sum(len(x["references"]) for x in targets),
                "unique_pdfs":len(targets), "targets":targets}
        # 공시 원본은 시각별로 보존하고 기존 계획도 백업한 뒤 교체한다.
        atomic_json(out / ("catalog_" + stamp + ".json"), rows)
        if (out / "plan.json").exists():
            shutil.copy2(out / "plan.json", out / ("plan_BACKUP_" + stamp + ".json"))
        atomic_json(out / "plan.json", plan)
        print(json.dumps({k:v for k,v in plan.items() if k != "targets"} | {"output_dir":str(out)}, ensure_ascii=False))
        return
    if not (out / "plan.json").exists():
        raise ValueError("Run plan and review it before start")
    # 부모와 자식에서 워커 락을 확인한다. 자식의 락 충돌은 기존 상태에 영향을 주지 않는다.
    with (out / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Download worker already running")
        fcntl.flock(lock, fcntl.LOCK_UN)
    with (out / "worker.log").open("ab") as log:
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker", str(out)],
                                 cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                                 start_new_session=True)
    print(json.dumps({"started":True,"pid":child.pid,"output_dir":str(out)}, ensure_ascii=False))

if __name__ == "__main__":
    main()
