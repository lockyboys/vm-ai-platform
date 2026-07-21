# SPS Current Checkpoint

Updated: 2026-07-21 KST

## Current Task
- Level 4 ID와 Domain Repository의 Source·DB 정합성을 마무리한다.

## Completed
- 모든 Table `_id` Level 4 형식 Migration 완료.
- 위반 98개 컬럼 전체 형식 위반 0건.
- 공식 Domain 교정 완료:
  - CM은 Common Business.
  - CO는 Common Domain.
  - SY는 공식 System Domain.
  - ID는 공식 Domain이 아니므로 Identifier Repository는 SP_RP.
- System Domain 복원 완료:
  - CM_SY_USER_LOGIN 2건.
  - CM_SY_PERMISSION 8건.
- Domain Field COMMENT Patch 28문장 SUCCESS.
- 9개 테이블, 18개 Domain 관련 컬럼 COMMENT 반영 및 18/18 검증 완료.
- COMMENT에 SSOT, 허용 코드, Repository First, Prefix 추론 및 Hardcoding 금지를 명시.
- Domain COMMENT 변경 전 Backup Table 9개 생성.

## Next Task
1. 전체 ID Business/Domain Prefix 전수 대조.
2. PK/FK 및 논리 참조 고아값 0건 검증.
3. Source Seed/Runtime SQL Legacy ID 검색 및 정비.
4. Git status 확인 후 Domain 교정 및 COMMENT 산출물 Commit.
5. 검증 완료 후 Backup Table Cleanup.

## Decisions
- Domain 값은 컬럼별 공식 Repository에서 해석한다.
- sp_* Object Domain SSOT는 sp_domain.
- business_domain_code SSOT는 cm_business_domain.
- Common 기능 Domain SSOT는 cm_common_code.CM_DOMAIN.
- Platform Domain SSOT는 cm_common_code.DOMAIN_CODE.
- Table Prefix 기반 Domain 추론을 금지한다.
