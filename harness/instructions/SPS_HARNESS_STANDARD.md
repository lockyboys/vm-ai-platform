# SPS Harness Standard

## Core Principles

- Repository First
- Generator First
- Metadata Driven
- Single Source of Truth
- Hardcoding Prohibited

## Working Method

- Continue from the current checkpoint.
- Do not restart completed repository analysis.
- Inspect the current file and database state before modification.
- Show the file to modify.
- Show how to locate the modification point.
- Show the content before modification.
- Show the content after modification.
- Run tests after modification.
- Verify actual table structures and stored rows.
- Preserve migration evidence.

## Database Rules

- Do not hardcode physical database names in Engine code.
- Resolve logical database roles through Repository metadata.
- Use snake_case for database objects.
- Use `_dt` for datetime columns.
- Use `_no` for integer sequence numbers.
- Use `_num` for numeric values represented as strings.
- Use Object noun plus `_description`.
- Description columns use VARCHAR(2000).
- Audit columns use:
  - created_dt
  - created_by
  - updated_dt
  - updated_by
  - deleted_by
  - deleted_dt
  - program_id
  - client_ip

## Safety Rules

- Do not expose secrets.
- Do not print passwords or tokens.
- Do not modify production resources without explicit approval.
- Do not commit automatically unless explicitly requested.
- Do not perform destructive database operations without evidence and verification.
