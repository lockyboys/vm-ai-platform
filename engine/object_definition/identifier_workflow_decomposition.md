# Identifier Workflow Legacy Decomposition

## Legacy Method Mapping

| Legacy Method | New Component | New Method |
|---|---|---|
| `_build_lock_name` | `IdentifierLockManager` | `build_lock_name` |
| `_acquire_lock` | `IdentifierLockManager` | `acquire` |
| `_release_lock` | `IdentifierLockManager` | `release` |
| `_ensure_sequence_metadata` | `IdentifierSequenceAllocator` | `ensure_sequence` |
| `_allocate_sequence` | `IdentifierSequenceAllocator` | `allocate` |
| `_validate_generated_identifier` | `IdentifierValidator` | `validate` |
| Blueprint 조회 | `IdentifierCoordinator` | `prepare` |
| Sequence Scope 결정 | `IdentifierCoordinator` | `prepare` |
| Identifier 렌더링 | `IdentifierCoordinator` | `resolve` |

## Responsibility

- `IdentifierCoordinator`
  - 식별자 발급 흐름 조정
- `IdentifierLockManager`
  - MariaDB Named Lock 관리
- `IdentifierSequenceAllocator`
  - Sequence Repository 준비 및 원자적 할당
- `IdentifierValidator`
  - 렌더링된 Identifier 검증
- `IdentifierEngine`
  - Blueprint 조회, 날짜 해석, Identifier 렌더링
