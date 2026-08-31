# SPS Gemini Operating Standard

Gemini works as an SPS coding agent through the configured `spsHarness` MCP server.

## Required workflow

1. Read `get_harness_instructions` and `get_current_checkpoint` before repository work.
2. Run `git_status` before modifying source and preserve all unrelated or pre-existing changes.
3. Use `source_search` and `source_read` before `source_patch` or `source_write`.
4. Use the existing Repository, Generator, metadata, and common implementations as the SSOT.
5. Do not hardcode Repository-managed values, database names, credentials, tokens, or secrets.
6. Run focused tests after every source change and inspect `git_diff`.
7. Never push. Commit only when the user explicitly requests it.
8. Database SQL may run only through registered Verified SQL Query IDs.
9. Keep mutation tools in dry-run mode until their targets and effects have been reviewed.
10. Never expose API keys, OAuth tokens, JWT signing keys, database passwords, or connector credentials.

## Source access

Gemini may use all tools exposed by `spsHarness`, including source inspection and patching,
test verification, Git inspection and guarded mutation, Repository inspection, MongoDB tools,
operational diagnostics, lifecycle reconciliation, and Verified SQL tools.

The Harness tool implementations remain the authorization and safety boundary. Do not bypass
their path checks, allowlists, dry-run defaults, OAuth requirements, or Repository contracts.
