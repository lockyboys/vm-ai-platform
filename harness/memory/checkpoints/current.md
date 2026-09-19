2026-09-18 01:08+09:00 verification
- After user restart: sps-harness MainPID=1607251, active/running, MCP /mcp 200 OK.
- Common-code SSOT patch is active: previous sp_business table error is gone.
- Both repository_table_object_reconcile(apply=false) and object_lifecycle_reconcile(apply=false) now stop at the next real contract inconsistency: table prefix CM maps to domain CO, but CM_DOMAIN common-code metadata has no CO code.
- Confirmed CM_BUSINESS and CM_DOMAIN groups/codes from cm_common_code/group. No DB mutation performed.
- Applied final message patch changing stale error text from cm_business_domain to CM_DOMAIN common-code metadata (SHA256=4ff6a31c6f07280073d89ecde985039ae4d6d5dda2d2ead48bbae20323169a20). Service restart required only to load this message patch.
- agent_long_term_memory remains 0; registration still not started. Do not invent CM->domain mapping or insert a new code without explicit data decision.