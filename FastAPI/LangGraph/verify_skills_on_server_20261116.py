"""서버 /data/vm_project/skills/ 에 넣은 스킬 4개가 원본과 같은지 검증한다 (2026-11-16, LuckyBoys 요청 "스킬 모아서 서버에 넣어 줘").

원본(Claude 작업 공간의 동기화된 스킬)에서 계산한 파일별 sha256 21개를 아래에 적어 두고 비교한다.
- 일치 / 다름 / 없음 / 목록에 없는 추가 파일을 모두 보고한다. 파일은 읽기만 한다.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "skills"
EXPECTED = {
    "chengyu-animated-shorts/SKILL.md": "4f4e85a508e611f1cf085872b5281d0fd9be7c94668d7c504d5daca34bd90114",
    "pick-stocks/SKILL.md": "a80929f0c11ee4d74e18bba292592deafff1eb3549f331f1369befb5a87f7264",
    "sps-orchestrator/SKILL.md": "f0ed343b1acb5585eba3f3f6018100904650c3373f309111826c7fb68836c806",
    "sps-orchestrator/references/architect.md": "38f5de7f145703c7ac7bd8a19ef6e7e32e570373d9ad4de43b4af363a61999cb",
    "sps-orchestrator/references/bug_hunter.md": "18a85d4e3cb2432fa1b6c57151ce6617f2747d4906ea5ffd576fe7d1e81e29fc",
    "sps-orchestrator/references/devops.md": "b5b8bb61d82faaa8edc7d4315b448e0dc1bc4fa5faf2389e6c79845bdad0d435",
    "sps-orchestrator/references/documenter.md": "2db39fc997bc1dfe57392eb5b311c9b9ac56a3f7aee0bb9ef0445d879afa5fa5",
    "sps-orchestrator/references/guidelines.md": "76937621c76111aa62601bc297c3989e77fa0f4dfb113800054916388b587ada",
    "sps-orchestrator/references/orchestrator.md": "1547813dc56c78a5943621a960e330bc3ac4428d24e52459840dfac59949836a",
    "sps-orchestrator/references/partner.md": "6d4475078ee3eb58c986ca53c279f5b3685e77384c4fc5dc343f1f0789498849",
    "sps-orchestrator/references/prompt_engineer.md": "4aee1552404ddf7c788a5337a1d8988f05e0ed79e137394cb1010c31e83044f2",
    "sps-orchestrator/references/reviewer.md": "196652d07389a6d7019b43d1ceab70c10ec560038b8d981543c6c4b02f83e536",
    "sps-orchestrator/references/security.md": "91a776c738b9e266ecb58281a7dde5f8450d98b6f828ddf40d795dbf686a0b53",
    "sps-orchestrator/references/sql_expert.md": "c3b0347fa8d3f0a20944d9efc8d5aaf912ca7016db7c7a6463fc733c053e87b6",
    "sps-orchestrator/references/strategist.md": "70b71c9621fcf75bbf6627430eeaed9ebd504d1b2c3ec41f464afb65712b2105",
    "sps-orchestrator/references/tester.md": "bea6c5d7f0f99f6ae0a732551f3709df4b95b022f11de43d59150004b52d7796",
    "sps-orchestrator/references/tutor.md": "75b53c58266f58033c6cdfeb516659824e5d846c95deca507531635db245ab06",
    "use-ulixee-hero-crawler/README.md": "b5b0cd93df0c49ccecb2be8aef3d9d9b64419a3652c0106aa3c29a14a0e0d212",
    "use-ulixee-hero-crawler/SKILL.md": "3e3b196e8f09a1b5e35f4a793e943277399f6609c7311b6bc7a8021130a80229",
    "use-ulixee-hero-crawler/agents/openai.yaml": "8cdd91b3ed618999d12e69d47599f6538a10d284a62e20d74dcde0b9cb3193e3",
    "use-ulixee-hero-crawler/assets/icon.svg": "0cdb7990dea3ad89ead04743eeac2dc58c119fb0b8b4a01499a21237f155bc1a",
}

report = {"match": [], "differ": [], "missing": [], "extra": []}
for rel, digest in EXPECTED.items():
    path = BASE / rel
    if not path.is_file():
        report["missing"].append(rel)
    elif hashlib.sha256(path.read_bytes()).hexdigest() == digest:
        report["match"].append(rel)
    else:
        report["differ"].append(rel)
if BASE.is_dir():
    report["extra"] = sorted(str(p.relative_to(BASE)) for p in BASE.rglob("*") if p.is_file()
                             and str(p.relative_to(BASE)) not in EXPECTED)
print(json.dumps({k: (v if k != "match" else len(v)) for k, v in report.items()}, ensure_ascii=False, indent=1))
print("판정:", "전부 일치" if len(report["match"]) == len(EXPECTED) and not report["extra"] else "불일치 있음")
