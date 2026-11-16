---
name: use-ulixee-hero-crawler
description: Use Ulixee Hero to inspect authorized dynamic websites, reuse user-provided authenticated sessions, pause for human CAPTCHA completion, classify SPA/list/detail behavior, and generate a resilient collection adapter without bypassing access controls.
---

# Use Ulixee Hero Crawler

## Purpose

Use this skill when the user supplies a webpage and asks to:

- perform a passive probe
- inspect an authenticated page the user is authorized to access
- reuse an existing browser profile, cookie jar, or storage state supplied by the user
- pause for the user to complete login, MFA, consent, or CAPTCHA manually, then resume
- determine whether content is SSR, CSR, SPA, hybrid, virtualized, paginated, or infinite-scroll
- detect list, map, modal, drawer, tab, popup, and detail-panel behavior
- identify stable DOM anchors and ordinary browser-visible network/state changes
- create, repair, or validate an Ulixee Hero collection adapter
- capture screenshots, HTML snippets, navigation transitions, and failure evidence

The skill is intended only for pages and accounts the user is authorized to inspect or collect.

## Security and authorization boundaries

Never:

- defeat, solve, outsource, or evade CAPTCHA or bot protection
- bypass login, paywalls, MFA, authorization checks, IP restrictions, access controls, or rate limits
- obtain or reuse credentials, cookies, sessions, tokens, or API keys without the account owner's authorization
- steal browser profiles, impersonate another user, or conceal automation to evade enforcement
- exploit vulnerabilities, enumerate unrelated endpoints, or probe systems outside the requested scope
- collect personal or sensitive data beyond the user's documented authorization
- submit forms, publish content, message people, change account settings, book, purchase, or delete without explicit instruction

Permitted authenticated workflow:

- let the user complete login, MFA, consent, or CAPTCHA through the site's normal interface
- reuse a browser profile, cookie file, or storage state that the authorized user explicitly provides
- attach to a user-controlled browser or persistent profile when supported by the installed tooling
- pause when a challenge appears and resume only after the user manually completes it
- use official APIs, exports, feeds, or partner endpoints when the user has legitimate access

A user statement such as “I own the account,” “I have written permission,” or an equivalent explicit authorization basis should be recorded in the probe report. Authorization does not permit technical circumvention of controls.

## Default workflow

### 1. Resolve the target and scope

Extract:

- exact target URL
- authorization basis
- account or workspace scope, if applicable
- desired output fields
- expected record limit
- whether authentication is already available
- acceptable session source: interactive login, persistent browser profile, cookie jar, storage state, or official API token
- expected output: probe report, adapter, dataset, screenshots, or all

Do not delay work for minor omissions. Use conservative defaults and visible placeholders.

### 2. Inspect the project before writing code

When project tools are available, inspect:

- `package.json`
- lockfiles
- installed Ulixee packages and exact versions
- existing Hero usage
- TypeScript configuration
- environment-variable conventions
- output and logging conventions

Use only APIs supported by the installed version. Do not invent imports or methods.

### 3. Establish an authorized browser session

Use the least intrusive available method, in this order:

1. existing user-controlled persistent browser profile
2. user-supplied storage state or cookie jar
3. interactive headful session where the user performs login/MFA/CAPTCHA
4. official API token or export path supplied by the user
5. public unauthenticated access

Session rules:

- never print secrets or full cookie values
- store secrets only through environment variables, secret stores, or user-approved local files
- redact authentication headers and cookie values from logs
- scope cookies to their original domain
- do not broaden privileges beyond the user's normal session
- detect session expiry and return to interactive re-authentication instead of attempting a bypass

### 4. Human-in-the-loop challenge handling

Detect likely login, MFA, consent, CAPTCHA, WAF, or access-control pages using:

- URL transitions
- HTTP status evidence when visible
- page titles and headings
- known challenge containers
- disappearance of expected content
- repeated redirects
- 401, 403, 407, 409, 423, or 429 responses

When a login, MFA, consent, or CAPTCHA challenge appears:

1. switch to or remain in visible/headful mode
2. capture a redacted screenshot and current URL
3. pause all automated interaction
4. ask the authorized user to complete the challenge manually
5. wait for a user-defined success condition, such as a post-login URL or expected DOM anchor
6. verify that the session is authenticated
7. resume from the last safe checkpoint

Do not click CAPTCHA answers, call CAPTCHA-solving services, rotate identities, alter fingerprints, or manipulate the challenge.

### 5. Passive probe first

Open the exact supplied URL and observe without destructive interaction:

- final URL and redirect chain
- page title
- visible headings and labels
- frame and iframe structure
- top-level DOM landmarks
- render timing and content-settle behavior
- dialogs, drawers, tabs, map overlays, and sticky panels
- links and buttons that appear to open details
- pagination controls
- infinite-scroll sentinels
- URL, history, and hash changes
- ordinary XHR/fetch activity visible through browser instrumentation
- console errors and failed resources
- authentication and challenge state

Capture evidence:

- initial screenshot
- post-render screenshot
- compact DOM snapshot
- candidate selectors
- interaction/result table
- redacted network summary
- session state: public, authenticated, expired, challenged, or blocked

### 6. Classify the page architecture

Choose one or more:

- SSR
- CSR/SPA
- hybrid rendering
- list-to-navigation detail
- list-to-modal detail
- list-to-side-panel detail
- map-marker-to-panel detail
- virtualized list
- infinite scroll
- paginated list
- API-backed state update
- authenticated workspace shell
- cross-origin iframe content

State the evidence for each classification.

### 7. Discover resilient extraction anchors

Prefer, in order:

1. semantic roles and accessible names
2. `data-*` attributes intended for testing or identity
3. stable IDs
4. repeated structural relationships
5. label/value relationships
6. text labels combined with local structure
7. stable URL or state identifiers
8. CSS classes only when demonstrably stable

Avoid:

- absolute DOM paths
- selectors composed only of generated class names
- positional selectors without an invariant parent
- hidden internal identifiers with no stable contract

For every field, record:

- field name
- source element or state
- primary selector strategy
- fallback strategy
- normalization rule
- missing-value behavior
- sensitivity classification

### 8. Exercise only authorized, reversible interactions

Permitted examples:

- scrolling
- opening and closing a visible detail panel
- switching read-only tabs
- clicking pagination controls
- selecting a list item or map marker
- expanding read-only accordions
- applying a user-requested read-only filter
- navigating within the user's authorized workspace

After every interaction, record:

- action
- target description
- URL before and after
- DOM change
- state or network change
- evidence screenshot when useful

Require explicit instruction before any action that can contact, save, favorite, submit, publish, reserve, purchase, edit, or delete.

### 9. Generate a resilient adapter

Default language: TypeScript.

The adapter should contain:

- typed configuration
- centralized selectors
- environment-based session configuration
- optional persistent profile or storage-state loading
- interactive authentication checkpoint
- challenge detection
- render-settle strategy
- bounded retry with capped attempts
- conservative concurrency
- list extraction
- detail opening and closing
- detail extraction
- pagination or infinite-scroll handling
- virtualized-list handling
- deduplication
- normalization
- structured evidence logging
- secret redaction
- screenshot-on-failure
- checkpoint/resume support
- deterministic JSON output
- explicit record, page, time, and error stop conditions

Do not hardcode secrets, credentials, target-specific tokens, or user identifiers.

### 10. Rate-limit and block handling

For 429, throttling banners, or obvious server pressure:

- stop new navigation
- honor `Retry-After` when available
- apply capped exponential backoff
- reduce concurrency
- save checkpoint state
- stop after the configured limit

For 401 or session expiry:

- save checkpoint
- return to interactive authentication
- resume only after the user restores access normally

For 403, WAF, IP restriction, or account restriction:

- capture redacted evidence
- stop automated attempts
- recommend an official API, export, allowlist, administrator approval, or site-supported access method

Never rotate proxies, identities, accounts, device fingerprints, or tokens to evade enforcement.

### 11. Validate minimally

Run the smallest non-destructive validation possible:

- load one page
- extract a small sample
- open one detail
- verify required fields
- close detail or return to list
- write sample JSON
- test checkpoint/resume once when practical

Report:

- records attempted
- records extracted
- missing fields
- duplicates
- selector failures
- session state
- challenge events
- blocked interactions

## Recommended project structure

```text
crawler/
├── config.ts
├── session.ts
├── challenge.ts
├── selectors.ts
├── types.ts
├── probe.ts
├── adapter.ts
├── normalize.ts
├── checkpoint.ts
├── evidence.ts
└── output/
```

Implementation requirements:

- one source of truth for selectors
- deterministic JSON schema
- bounded concurrency and retries
- delay/jitter only for site stability, never evasion
- explicit rate limit
- resumable cursor or page state
- secret redaction
- screenshots and HTML snippets only on failure or explicit request
- no personal-data persistence unless explicitly authorized
- smallest possible sample during validation

## Probe report format

```markdown
# Passive Probe Report

## Target
- URL:
- Checked at:
- Authorization basis:
- Requested scope:

## Session
- Mode: public / persistent profile / storage state / interactive login / official API
- State: authenticated / expired / challenged / blocked
- Secret logging: redacted

## Rendering model
- Classification:
- Evidence:

## List behavior
- Container:
- Item anchor:
- Pagination/scroll:

## Detail behavior
- Open method:
- Surface: navigation/modal/drawer/panel
- Close/return method:

## Candidate fields
| Field | Primary anchor | Fallback | Sensitivity | Notes |
|---|---|---|---|---|

## Challenge and access handling
- Login/MFA:
- CAPTCHA:
- WAF/access control:
- Rate limiting:
- Resume condition:

## Adapter plan
- Files:
- Session source:
- Stop conditions:
- Validation sample:
```

## Invocation behavior

When invoked as:

`$use-ulixee-hero-crawler passive probe <URL>`

perform the probe first and return the report before proposing large-scale collection.

When invoked as:

`$use-ulixee-hero-crawler authenticated probe <URL>`

perform:

1. inspect available authorized session methods
2. start or attach to a visible session
3. pause for manual login, MFA, consent, or CAPTCHA when needed
4. verify the post-authentication anchor
5. continue with passive probe
6. return a redacted probe report

When invoked as:

`$use-ulixee-hero-crawler <URL> 목록과 상세 동작을 판별하고 수집 어댑터를 만들어줘`

perform:

1. passive or authenticated probe
2. architecture classification
3. selector map
4. adapter implementation
5. small non-destructive validation
6. diff and exact run command

When project write tools are available, modify the actual project. Otherwise, return complete files with explicit paths.

## Failure handling

- If Ulixee Hero is missing, inspect dependencies and provide the exact package-manager command.
- If the page is unreachable, preserve the error and stop.
- If login is required, open an interactive session or use a user-supplied authorized profile/state; never request the user's password in chat.
- If MFA, consent, or CAPTCHA appears, pause and let the user complete it manually, then verify and resume.
- If access control or WAF blocking remains after normal authorized access, preserve evidence and stop rather than escalating attempts.
- If selectors are unstable, produce a selector-risk table rather than claiming reliability.
- If authorization is unclear, limit work to public passive probing.

## Quality bar

A successful result must be reproducible, bounded, redacted, checkpointed, and honest about blockers. Never claim that any crawler can access every website or defeat every protection.
