"""PDF 첫 페이지 제목으로 사본을 저장한다. 원본 PDF와 수집 기록은 유지한다."""
from __future__ import annotations
import fcntl
import concurrent.futures
import multiprocessing
import unittest
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def page_lines(path):
    """첫 페이지의 텍스트·글자 크기·위치를 읽는다. PDF 자체는 쓰지 않는다."""
    import fitz
    with fitz.open(path) as document:
        page = document[0]
        result = []
        for block_no, block in enumerate(page.get_text("dict")["blocks"]):
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                text = re.sub(r"\s+", " ", "".join(span["text"] for span in spans)).strip()
                if text:
                    result.append({"text": text, "size": round(max(s["size"] for s in spans), 2),
                                   "y": round(line["bbox"][1], 2), "block": block_no})
        return sorted(result, key=lambda row: row["y"])


def title_from_lines(lines):
    """제목 후보가 없거나 일반 목차 제목뿐이면 추정하지 않고 빈 값을 반환한다."""
    generic = {"약관", "보험약관", "보험약관집", "목차", "보통약관", "주계약약관", "aia", "aia생명"}
    candidates = []
    for index, row in enumerate(lines):
        compact = re.sub(r"\s+", "", row["text"])
        if compact.lower() in generic or len(compact) < 5 or len(row["text"]) > 150:
            continue
        if "보험" not in compact and "특약" not in compact:
            continue
        if any(term in compact for term in ("보험금청구", "보험계약자", "보험가입", "보험금지급", "보험계약체결", "보험계약관리", "보험료납입", "보험계약대출", "보험계약의")):
            continue
        score = row["size"] + (15 if "무배당" in compact else 0) + (10 if "약관" in compact else 0)
        candidates.append((score, index))
    if not candidates:
        return ""
    _, index = max(candidates)
    anchor = lines[index]
    chosen = [anchor]
    for row in lines:
        if row is anchor:
            continue
        if row["block"] == anchor["block"] and abs(row["y"] - anchor["y"]) < 100 and row["size"] >= anchor["size"] * .7:
            if len(row["text"]) < 130:
                chosen.append(row)
    # '무배당'이 별도 텍스트 블록인 표지도 첫 페이지에서 읽은 그대로 결합한다.
    for row in lines:
        if row["text"].replace(" ", "") in {"무배당", "(무)", "(무배당)"} and 0 <= anchor["y"] - row["y"] < 80:
            if row not in chosen:
                chosen.append(row)
    title = " ".join(row["text"] for row in sorted(chosen, key=lambda row: row["y"]))
    return re.sub(r"\s+", " ", title).strip()


def safe_name(title, period, server):
    """원문 제목은 index에 보존하고 파일명에서만 금지 문자·길이를 처리한다."""
    text = unicodedata.normalize("NFC", title)
    text = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", text).strip(" .")
    text = text.encode("utf-8")[:150].decode("utf-8", errors="ignore").strip(" .")
    if not text:
        raise ValueError("제목 파일명 생성 불가")
    return text + "_" + period + "__" + Path(server).stem + ".pdf"


def sha(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def context():
    import config
    from common.common_function import normalize_required_text
    return Path(normalize_required_text(str(config.OUTPUT_PATH), "OUTPUT_PATH")).resolve() / "insurance_docs/AIA"


def atomic_json(path, value):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temp, path)


def ocr_lines(path, region=None):
    """PDF 첫 페이지 이미지를 기존 image_analyzer의 OCR 함수로 분석한다."""
    import fitz
    from image_analyzer import extract_text_from_image
    with tempfile.TemporaryDirectory(prefix="aia_title_ocr_") as directory:
        image = Path(directory) / "page.png"
        with fitz.open(path) as document:
            page = document[0]
            # 본문을 제목으로 오인하지 않도록 첫 페이지의 상단 표지 영역만 OCR한다.
            rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * .6)
            title_spans = [span for block in page.get_text("dict")["blocks"]
                for line in block.get("lines", []) for span in line.get("spans", [])
                if span["bbox"][1] < page.rect.height * .65 and span.get("text", "").strip()]
            if region == "header":
                rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * .13)
            elif region == "cover":
                rect = fitz.Rect(0, 0, page.rect.width, page.rect.height * .65)
            elif title_spans:
                largest = max(span["size"] for span in title_spans)
                large = [span for span in title_spans if span["size"] >= largest * .65]
                left = min(span["bbox"][0] for span in large)
                top = min(span["bbox"][1] for span in large)
                right = max(span["bbox"][2] for span in large)
                bottom = max(span["bbox"][3] for span in large)
                rect = fitz.Rect(left - 5, top - 5, right + 5, bottom + 5) & page.rect
            page.get_pixmap(matrix=fitz.Matrix(3, 3) if region else fitz.Matrix(2, 2), clip=rect).save(image)
        # 개정 이력의 표지가 같으면 기존 이미지 분석 결과를 재사용한다.
        cache = context() / "first_page_titles" / "ocr_cache"
        cache.mkdir(parents=True, exist_ok=True)
        cached = cache / (sha(image) + ".json")
        if cached.exists():
            return json.loads(cached.read_text(encoding="utf-8"))
        text = extract_text_from_image(image)
        lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines() if line.strip()]
        result = [{"text": line, "size": 20, "y": index * 25, "block": index}
                  for index, line in enumerate(lines)]
        temporary = cached.with_suffix("." + str(os.getpid()) + ".tmp")
        temporary.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
        os.replace(temporary, cached)
        return result


def needs_ocr(lines):
    """큰 글자가 이미 온전한 한글이면 같은 페이지의 OCR을 반복하지 않는다."""
    if not lines:
        return True
    largest = max(row["size"] for row in lines)
    heading = "".join(row["text"] for row in lines if row["size"] >= largest * .8)
    compact = re.sub(r"\s+", "", heading)
    return not compact or len(re.findall(r"[가-힣]", compact)) / len(compact) < .5


def scan_one(item):
    source = Path(item["path"])
    base = {"source": source.name, "period": item["period"], "sha256": item.get("sha256")}
    if not source.is_file():
        return {**base, "status": "SOURCE_MISSING"}
    try:
        lines = page_lines(source)
        title = title_from_lines(lines)
        method = "first_page_text"
        if not title and needs_ocr(lines):
            lines = ocr_lines(source)
            title = title_from_lines(lines)
            method = "first_page_ocr"
        if not title:
            return {**base, "status": "TITLE_UNCONFIRMED"}
        return {**base, "status": "TITLE_EXTRACTED", "title": title, "method": method,
                "filename": safe_name(title, item["period"], source.name), "bytes": source.stat().st_size}
    except Exception as error:
        return {**base, "status": "READ_FAILED", "error_type": type(error).__name__}


def recover_one(record):
    path = context() / "pdf" / record["source"]
    if not path.is_file():
        return record
    try:
        lines = page_lines(path)
        attempts = []
        for region in ("header", "cover"):
            # 안내문이 빽빽한 첫 페이지에서는 상단 상품명만 읽는다.
            if region == "cover" and len(lines) > 8:
                continue
            found = ocr_lines(path, region=region)
            title = title_from_lines(found)
            attempts.append({"region": region, "text": [r["text"] for r in found]})
            if title:
                return {**record, "status": "TITLE_EXTRACTED", "title": title,
                        "method": "first_page_ocr_" + region, "ocr_evidence": attempts,
                        "filename": safe_name(title, record["period"], path.name),
                        "bytes": path.stat().st_size}
        return {**record, "ocr_evidence": attempts}
    except Exception as exc:
        return {**record, "status": "READ_FAILED", "error_type": type(exc).__name__}


def recover_worker(out, folder):
    records = [json.loads(line) for line in (folder / "scan.jsonl").read_text(encoding="utf-8").splitlines()]
    pending = [r for r in records if r["status"] != "TITLE_EXTRACTED"]
    log_path = folder / "recovery.jsonl"
    previous = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()] if log_path.exists() else []
    done = {r["source"] for r in previous}
    state = {"state": "RECOVERING", "expected": len(pending), "finished": len(previous),
             "additional_copies": sum(r.get("copy_status") == "COPY_VERIFIED" for r in previous)}
    atomic_json(folder / "recovery_status.json", state)
    with log_path.open("a", encoding="utf-8") as stream:
        with concurrent.futures.ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("fork")) as pool:
            for record in pool.map(recover_one, [r for r in pending if r["source"] not in done], chunksize=1):
                if record["status"] == "TITLE_EXTRACTED":
                    source = out / "pdf" / record["source"]
                    target = out / "first_page_named" / record["filename"]
                    temporary = None
                    try:
                        if target.exists() or target.is_symlink():
                            raise ValueError("기존 파일 덮어쓰기 금지")
                        fd, name = tempfile.mkstemp(prefix=".recovery_", dir=target.parent)
                        temporary = Path(name)
                        with os.fdopen(fd, "wb") as output, source.open("rb") as original:
                            shutil.copyfileobj(original, output, 1024 * 1024)
                        if not record.get("sha256") or sha(temporary) != record["sha256"]:
                            raise ValueError("수집 원본과 SHA256 불일치")
                        os.link(temporary, target)
                        # 공개 공시 약관은 별도 SFTP 계정에서도 내려받을 수 있게 한다.
                        os.chmod(target, 0o644)
                        record["copy_status"] = "COPY_VERIFIED"
                        state["additional_copies"] += 1
                    except Exception as exc:
                        record.update(copy_status="FAILED", copy_error_type=type(exc).__name__)
                    finally:
                        if temporary is not None:
                            temporary.unlink(missing_ok=True)
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                stream.flush()
                previous.append(record)
                state["finished"] += 1
                atomic_json(folder / "recovery_status.json", state)
    verified = [json.loads(line) for line in (folder / "copies.jsonl").read_text(encoding="utf-8").splitlines()]
    total = sum(r.get("status") == "COPY_VERIFIED" for r in verified) + state["additional_copies"]
    state.update(state="PARTIAL" if total < len(records) else "COMPLETED", total_verified_copies=total,
                 remaining=len(records) - total)
    atomic_json(folder / "recovery_status.json", state)
    atomic_json(folder / "status.json", {**state, "output_dir": str(out / "first_page_named")})


def worker(operation):
    """원본 읽기/사본 생성의 진행률을 파일에 남긴다. 전체 성공 여부를 분리한다."""
    out = context()
    folder = out / "first_page_titles"
    with (folder / "worker.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if operation == "recover":
            recover_worker(out, folder)
            return
        if operation == "scan":
            plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
            manifest = {}
            for line in (out / "manifest.jsonl").read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row.get("status") in {"downloaded_verified", "existing_verified"}:
                    manifest[row["server_file"]] = row["sha256"]
            items = []
            for target in plan["targets"]:
                name = target["server_file"]
                if Path(name).name != name:
                    raise ValueError("원본 경로 오류")
                reference = target["references"][0]
                dates = str(reference.get("pro_start_date") or "미확인") + "~" + str(reference.get("pro_end_date") or "미확인")
                dates = re.sub(r'[^0-9가-힣~_-]', '', dates)[:30]
                items.append({"path": str(out / "pdf" / name), "period": dates, "sha256": manifest.get(name)})
            records = folder / "scan.jsonl"
            existing = [json.loads(line) for line in records.read_text(encoding="utf-8").splitlines()] if records.exists() else []
            completed = {row["source"] for row in existing}
            state = {"state": "SCANNING", "expected": len(items), "finished": len(existing),
                     "titled": sum(row["status"] == "TITLE_EXTRACTED" for row in existing),
                     "unconfirmed": sum(row["status"] != "TITLE_EXTRACTED" for row in existing)}
            items = [item for item in items if Path(item["path"]).name not in completed]
            atomic_json(folder / "status.json", state)
            with records.open("a", encoding="utf-8") as stream:
                with concurrent.futures.ProcessPoolExecutor(max_workers=2, mp_context=multiprocessing.get_context("fork")) as pool:
                    for record in pool.map(scan_one, items, chunksize=1):
                        stream.write(json.dumps(record, ensure_ascii=False) + "\n")
                        stream.flush()
                        state["finished"] += 1
                        state["titled" if record["status"] == "TITLE_EXTRACTED" else "unconfirmed"] += 1
                        if state["finished"] % 20 == 0:
                            atomic_json(folder / "status.json", state)
            state["state"] = "SCANNED"
            atomic_json(folder / "status.json", state)
            return
        if operation != "apply":
            raise ValueError("지원하지 않는 작업")
        previous = json.loads((folder / "status.json").read_text(encoding="utf-8"))
        if previous["state"] != "SCANNED":
            raise ValueError("첫 페이지 제목 추출이 끝나야 합니다")
        records = [json.loads(line) for line in (folder / "scan.jsonl").read_text(encoding="utf-8").splitlines()]
        entries = [row for row in records if row["status"] == "TITLE_EXTRACTED"]
        if shutil.disk_usage(out).free < sum(row["bytes"] for row in entries) + 1024**3:
            raise OSError("사본을 만들 여유 공간이 부족합니다")
        destination = out / "first_page_named"
        destination.mkdir(exist_ok=True)
        state = {"state": "APPLYING", "expected": len(entries), "finished": 0, "created": 0,
                 "failed": 0, "title_unconfirmed": len(records) - len(entries)}
        atomic_json(folder / "status.json", state)
        with (folder / "copies.jsonl").open("x", encoding="utf-8") as stream:
            for record in entries:
                source = out / "pdf" / record["source"]
                target = destination / record["filename"]
                result = {"source": record["source"], "filename": record["filename"]}
                temporary = None
                try:
                    if target.exists() or target.is_symlink():
                        raise ValueError("기존 사본 덮어쓰기 금지")
                    fd, name = tempfile.mkstemp(prefix=".title_", dir=destination)
                    temporary = Path(name)
                    with os.fdopen(fd, "wb") as output, source.open("rb") as original:
                        shutil.copyfileobj(original, output, 1024 * 1024)
                    digest = sha(temporary)
                    if not record.get("sha256") or digest != record["sha256"]:
                        raise ValueError("원본 수집 기록과 사본 SHA256 불일치")
                    os.link(temporary, target)
                    # mkstemp의 기본 0600을 사본에 남기지 않아 SFTP 다운로드를 허용한다.
                    os.chmod(target, 0o644)
                    state["created"] += 1
                    result.update(status="COPY_VERIFIED", sha256=digest)
                except Exception as error:
                    state["failed"] += 1
                    result.update(status="FAILED", error_type=type(error).__name__)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
                stream.write(json.dumps(result, ensure_ascii=False) + "\n")
                stream.flush()
                state["finished"] += 1
                if state["finished"] % 20 == 0:
                    atomic_json(folder / "status.json", state)
        state.update(state="COMPLETED" if not state["failed"] and not state["title_unconfirmed"] else "PARTIAL",
                     output_dir=str(destination))
        atomic_json(folder / "status.json", state)


class TitleTests(unittest.TestCase):
    def test_readable_generic_does_not_need_ocr(self):
        self.assertFalse(needs_ocr([{"text":"목차","size":30}]))
    def test_broken_font_needs_ocr(self):
        self.assertTrue(needs_ocr([{"text":"芛莗穠迗脤鲿移","size":50}]))
    def test_split_cover(self):
        rows = [{"text":"무배당","size":35,"y":90,"block":3}, {"text":"여유+ 변액연금보험","size":53,"y":133,"block":6}, {"text":"약관","size":27,"y":256,"block":4}]
        self.assertEqual(title_from_lines(rows), "무배당 여유+ 변액연금보험")
    def test_generic_title_rejected(self):
        self.assertEqual(title_from_lines([{"text":"보험약관","size":30,"y":10,"block":0}]), "")
    def test_empty_rejected(self):
        self.assertEqual(title_from_lines([]), "")
    def test_safe_filename(self):
        self.assertNotIn("/", safe_name("보험/약관", "20260101~현재", "ID.pdf"))
    def test_length_bounded(self):
        self.assertLess(len(safe_name("가" * 1000, "20260101~현재", "ID.pdf").encode()), 255)


def main():
    if sys.argv[1:2] == ["--worker"]:
        worker(sys.argv[2])
        return
    options = json.loads(sys.stdin.read() or "{}")
    mode = options.get("mode", "inspect")
    if mode == "self_test":
        result = unittest.TextTestRunner().run(unittest.defaultTestLoader.loadTestsFromTestCase(TitleTests))
        print(json.dumps({"passed": result.wasSuccessful(), "tests": result.testsRun}))
        if not result.wasSuccessful():
            raise SystemExit(1)
        return
    out = context()
    folder = out / "first_page_titles"
    if mode == "trim_named_copy":
        import stat
        # Windows 대상 경로가 거부하는 선행 공백만 지정된 제목 사본에서 제거한다.
        old_name = options["filename"]
        if Path(old_name).name != old_name or not old_name.startswith("  ") or not old_name.endswith(".pdf"):
            raise ValueError("대상 이름 오류")
        old = out / "first_page_named" / old_name
        new = old.with_name(old_name.lstrip())
        original = old.lstat()
        if not stat.S_ISREG(original.st_mode) or original.st_uid != os.geteuid() or new.exists() or new.is_symlink():
            raise ValueError("원본 종류·소유권 또는 대상 충돌")
        if options.get("apply") is True:
            # 먼저 새 이름을 같은 파일에 연결하고 해시를 확인한 뒤 이전 이름만 해제한다.
            os.link(old, new)
            if sha(old) != sha(new):
                new.unlink()
                raise ValueError("내용 검증 실패")
            old.unlink()
        print(json.dumps({"old": old_name, "new": new.name,
                          "apply": options.get("apply") is True,
                          "old_exists": old.exists(), "new_exists": new.exists(),
                          "bytes": original.st_size}, ensure_ascii=False))
        return
    if mode == "single_permission":
        import stat
        # 공백을 제외한 사용자의 정확한 파일명 하나만 대상으로 삼는다.
        requested = options["filename"]
        normalized = re.sub(r"\s+", "", requested)
        if Path(requested).name != requested or not normalized.endswith(".pdf"):
            raise ValueError("파일명 오류")
        directory = out / "first_page_named"
        matches = [entry for entry in directory.iterdir()
                   if re.sub(r"\s+", "", entry.name) == normalized]
        if len(matches) != 1:
            print(json.dumps({"matches": len(matches), "filename": requested}, ensure_ascii=False))
            return
        target = matches[0]
        info = target.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise ValueError("일반 파일·소유권 검증 실패")
        old = stat.S_IMODE(info.st_mode)
        if options.get("apply") is True and old != 0o644:
            target.chmod(0o644)
        current = stat.S_IMODE(target.stat().st_mode)
        print(json.dumps({"filename": target.name, "before": oct(old),
                          "after": oct(current), "applied": options.get("apply") is True,
                          "bytes": target.stat().st_size}, ensure_ascii=False))
        return
    if mode == "repair_copy_permissions":
        import stat
        # 검증 기록에 들어 있는 이 디렉터리의 정상 사본만 선택한다.
        destination = out / "first_page_named"
        records = []
        for log_name, status_key, ok in (("copies.jsonl", "status", "COPY_VERIFIED"),
                                         ("recovery.jsonl", "copy_status", "COPY_VERIFIED")):
            for line in (folder / log_name).read_text(encoding="utf-8").splitlines():
                record = json.loads(line)
                if record.get(status_key) == ok:
                    records.append(record)
        seen = set()
        changed = 0
        sample = []
        missing = []
        for record in records:
            name = record["filename"]
            if Path(name).name != name or name in seen:
                raise ValueError("검증 기록의 중복·경로 오류")
            seen.add(name)
            path = destination / name
            try:
                info = path.lstat()
            except FileNotFoundError:
                # 사용자가 이동/삭제한 사본은 새로 만들거나 권한을 바꾸지 않는다.
                missing.append(name)
                continue
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
                raise ValueError("검증된 일반 파일의 소유권 확인 실패")
            old_mode = stat.S_IMODE(info.st_mode)
            if old_mode != 0o644:
                changed += 1
                if len(sample) < 3:
                    sample.append({"name": name, "from": oct(old_mode), "to": "0o644"})
                if options.get("apply") is True:
                    path.chmod(0o644)
        print(json.dumps({"apply": options.get("apply") is True,
                          "verified_records": len(records), "present": len(records) - len(missing),
                          "missing_count": len(missing), "missing_examples": missing[:3],
                          "change_count": changed, "sample": sample}, ensure_ascii=False))
        return
    if mode == "permission_probe":
        import stat
        import pwd
        import grp
        # SFTP 오류의 실제 경로만 조회하고 파일 내용과 인증 정보는 출력하지 않는다.
        name = options["filename"]
        if Path(name).name != name or not name.endswith(".pdf"):
            raise ValueError("파일 이름 오류")
        target = out / "first_page_named" / name
        paths = [out.parent.parent.parent.parent, out.parent.parent.parent,
                 out.parent.parent, out.parent, out,
                 target.parent, target]
        result = []
        for path in paths:
            info = path.lstat()
            result.append({"path": str(path), "mode": oct(stat.S_IMODE(info.st_mode)),
                           "uid": info.st_uid, "gid": info.st_gid,
                           "regular": stat.S_ISREG(info.st_mode),
                           "directory": stat.S_ISDIR(info.st_mode), "bytes": info.st_size})
        users = []
        for name in ("jeaje", "sftpuser"):
            try:
                account = pwd.getpwnam(name)
                group_ids = sorted({account.pw_gid, *os.getgrouplist(name, account.pw_gid)})
                users.append({"name": name, "uid": account.pw_uid,
                              "groups": [grp.getgrgid(group).gr_name for group in group_ids],
                              "home": account.pw_dir})
            except KeyError:
                users.append({"name": name, "missing": True})
        print(json.dumps({"euid": os.geteuid(), "paths": result, "users": users}, ensure_ascii=False))
        return
    folder.mkdir(exist_ok=True)
    if mode == "diagnose_pending":
        from collections import Counter
        records = [json.loads(line) for line in (folder / "scan.jsonl").read_text(encoding="utf-8").splitlines()]
        pending = [r for r in records if r["status"] != "TITLE_EXTRACTED"]
        examples = []
        for row in pending[int(options.get("offset", 0)):int(options.get("offset", 0)) + int(options.get("limit", 15))]:
            path = out / "pdf" / row["source"]
            try:
                lines = page_lines(path) if path.is_file() else []
                examples.append({**row, "needs_ocr": needs_ocr(lines), "lines": lines[:12]})
            except Exception as exc:
                examples.append({**row, "error_type": type(exc).__name__})
        print(json.dumps({"counts": dict(Counter(r["status"] for r in pending)), "examples": examples}, ensure_ascii=False))
        return
    if mode == "recovery_status":
        print((folder / "recovery_status.json").read_text(encoding="utf-8"))
        return
    if mode == "status":
        state = json.loads((folder / "status.json").read_text(encoding="utf-8")) if (folder / "status.json").exists() else {"state": "NOT_STARTED"}
        print(json.dumps(state, ensure_ascii=False))
        return
    if mode == "stop_scan":
        import signal
        pid = int(options["pid"])
        command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ")
        if b"haness/aia_first_page_names.py --worker scan" not in command or os.getpgid(pid) != pid:
            raise ValueError("현재 제목 추출 워커가 아닙니다")
        os.killpg(pid, signal.SIGTERM)
        print(json.dumps({"stopped_scan_pid": pid}))
        return
    if mode == "start":
        operation = options.get("operation", "scan")
        if operation not in {"scan", "apply", "recover"}:
            raise ValueError("지원하지 않는 작업")
        folder.mkdir(exist_ok=True)
        with (folder / "worker.log").open("ab") as log:
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--worker", operation],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
                env={**os.environ, "OMP_NUM_THREADS":"1", "MKL_NUM_THREADS":"1", "OPENBLAS_NUM_THREADS":"1"})
        print(json.dumps({"started": True, "pid": child.pid, "operation": operation}, ensure_ascii=False))
        return
    if mode == "probe_ocr":
        plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
        path = out / "pdf" / plan["targets"][0]["server_file"]
        lines = ocr_lines(path)
        print(json.dumps({"ocr_module": "image_analyzer", "title": title_from_lines(lines), "lines": lines[:8]}, ensure_ascii=False))
        return
    if mode != "inspect":
        raise ValueError("지원하지 않는 모드")
    plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
    targets = plan["targets"]
    indices = options.get("indices", [0, 1, 100, 1000, 3000, 4993])
    examples = []
    for index in indices:
        target = targets[index]
        path = out / "pdf" / target["server_file"]
        lines = page_lines(path) if path.exists() else []
        examples.append({"source": path.name, "extracted_title": title_from_lines(lines), "lines": lines[:15]})
    print(json.dumps({"examples": examples}, ensure_ascii=False))


if __name__ == "__main__":
    main()
