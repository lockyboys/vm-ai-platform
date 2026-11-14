"""SPS 13개 페르소나 공통 기능 (2026-10-25 LuckyBoys: persona_source 중복을 common으로 빼기).

왜 있나
    haness/mcp/agents/persona_source_runtime.py(앱 대상 동적 페르소나)와
    haness/mcp/agents/persona_repair_chain.py(수집기 자기 수리)가 같은 일을 따로 구현하고 있었다.
    - 프롬프트 출처가 달랐다(AdvancedPersonas 내장 문자열 vs 스킬 원문 파일)
    - 계획 해석이 둘(JSON {"personas":[...]} vs 'PLAN:' 줄), Gemini 블록 응답 처리가 한쪽에만 있었다
    그래서 공통 부분만 이 한 클래스로 모은다. 그래프·도구·대상(앱/소스) 실행은 각 런타임에 남긴다.

제공 기능 (PersonaSource)
    load(name) / load_all(names) : persona_dir/<이름>.md 원문을 그대로 읽는다(사용자 원문 그대로 — 변경·대체 없음)
    available(exclude)           : 원문 파일이 있는 페르소나 이름
    content_text(content)        : LLM 응답(content)이 Gemini 블록 목록이어도 텍스트만 꺼낸다(repr 파싱 금지)
    parse_plan_json(...)         : {"personas":[...]} 계획. 잘못되면 ValueError(대체 계획 없음), 순서·재호출 보존
    parse_plan_line(...)         : 마지막 'PLAN: A, B' 줄 계획. 줄이 없으면 None, 중복 제거·상한 자르기
    parse_verdict(text)          : 마지막 'VERDICT: X'. 없으면 '미확인'

설정: 루트 config.py SPS_PERSONA_PROMPTS['persona_dir'] (일반 지침 4). DB 사용 없음.
주의: max_personas 같은 호출 상한은 호출하는 런타임 설정을 인자로 받는다(런타임마다 상한이 다를 수 있음).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

import config

# 스킬 SKILL.md 담당 페르소나 표의 13개 이름(파일명은 소문자 .md)
PERSONA_NAMES = ("ORCHESTRATOR", "ARCHITECT", "SQL_EXPERT", "PROMPT_ENGINEER", "STRATEGIST", "PARTNER",
                 "REVIEWER", "SECURITY", "TESTER", "BUG_HUNTER", "DEVOPS", "DOCUMENTER", "TUTOR")
_NAME = re.compile(r"[A-Z_]{2,32}")
_VERDICT = re.compile(r"VERDICT:\s*([A-Z_]+)")


class PersonaSource:
    """페르소나 원문 프롬프트와 계획·판정 해석을 한곳에서 제공한다."""

    def __init__(self, persona_dir: str | Path | None = None):
        # 기본 위치는 루트 config(일반 지침 4). 테스트·다른 런타임은 경로를 직접 줄 수 있다.
        self.persona_dir = Path(str(persona_dir or config.SPS_PERSONA_PROMPTS["persona_dir"]))

    # --- 프롬프트 ---------------------------------------------------------------
    def load(self, name: str) -> str:
        """원문 프롬프트를 그대로 읽는다. 이름이 잘못되거나 파일이 없으면 예외(다른 프롬프트로 대체하지 않음)."""
        if not isinstance(name, str) or not _NAME.fullmatch(name):
            raise ValueError(f"invalid persona name: {name!r}")
        return (self.persona_dir / f"{name.lower()}.md").read_text(encoding="utf-8")

    def load_all(self, names: Iterable[str] = PERSONA_NAMES) -> dict[str, str]:
        """여러 페르소나 원문을 {이름: 프롬프트}로 읽는다(하나라도 없으면 예외)."""
        return {name: self.load(name) for name in names}

    def available(self, exclude: Iterable[str] = ("ORCHESTRATOR",)) -> list[str]:
        """원문 파일이 실제로 있는 페르소나 이름(정렬). 계획의 선택지로 쓴다."""
        skip = set(exclude)
        names = sorted(p.stem.upper() for p in self.persona_dir.glob("*.md"))
        return [n for n in names if n not in skip and _NAME.fullmatch(n)]

    # --- 응답 해석 ---------------------------------------------------------------
    @staticmethod
    def content_text(content: Any) -> str:
        """LLM 응답 content를 텍스트로 만든다. Gemini는 [{'type':'text','text':...}, ...] 블록을 줄 수 있다."""
        if isinstance(content, list):
            return "".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")
        if not isinstance(content, str):
            raise ValueError("model response must contain text")
        return content

    def parse_plan_json(self, content: Any, allowed: Iterable[str], max_personas: int) -> list[str]:
        """{"personas":[...]} 계획을 검증한다. 순서와 같은 역할 재호출을 그대로 둔다. 잘못되면 ValueError."""
        text = self.content_text(content).strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
        value = json.loads(text)   # JSON이 아니면 json.JSONDecodeError(ValueError 하위)
        roles = value.get("personas") if isinstance(value, dict) else None
        if not isinstance(roles, list) or not 1 <= len(roles) <= int(max_personas):
            raise ValueError("invalid persona plan length")
        allowed_set = set(allowed)
        if any(not isinstance(r, str) or r not in allowed_set for r in roles):
            raise ValueError("unknown or ineligible persona")
        return roles

    def parse_plan_line(self, content: Any, allowed: Iterable[str],
                        max_personas: int) -> tuple[list[str] | None, list[str]]:
        """마지막 'PLAN: A, B' 줄 → (쓴 순서대로 고른 페르소나, 무시된 이름). 줄이 없으면 (None, []).

        중복은 첫 번째만 남기고, 마지막 통합 1회를 위해 max_personas - 1개까지만 남긴다.
        """
        text = self.content_text(content)
        lines = [l for l in text.splitlines() if l.strip().upper().startswith("PLAN:")]
        if not lines:
            return None, []
        names = [n.strip().upper() for n in re.split(r"[,\s→>]+", lines[-1].split(":", 1)[1]) if n.strip()]
        allowed_list = list(allowed)
        selected: list[str] = []
        for name in names:
            if name in allowed_list and name not in selected:
                selected.append(name)
        selected = selected[: max(0, int(max_personas) - 1)]
        return selected, sorted({n for n in names if n not in allowed_list})

    def parse_verdict(self, content: Any) -> str:
        """마지막 'VERDICT: X'를 읽는다. 없으면 '미확인'(판정 없는 통과 금지)."""
        found = _VERDICT.findall(self.content_text(content or ""))
        return found[-1] if found else "미확인"
