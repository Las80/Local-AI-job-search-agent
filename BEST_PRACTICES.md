# Best Practices — Instructions for AI Coding Assistants

This document is written as instructions to an AI coding assistant working on the Local AI Job Search Agent. Follow these rules when making changes.

---

## 1. CODE REVIEW PROTOCOL

- Before making any change, read every existing file in the project that is relevant to the task.
- State what you are changing and why before touching anything.
- After making a change, re-read the modified file to confirm correctness.
- Never change a file that belongs to a completed slice unless the change is an explicit, named patch (see Slice Isolation Rule).

---

## 2. SLICE ISOLATION RULE

- The project is developed in slices (see SLICE_PLAN.md). Each slice is developed and tested independently.
- If a later slice reveals a bug in an earlier slice, fix it as a **named patch** (e.g. document "Patch: fix X in slice Y" and then make the minimal change).
- Never silently modify a completed slice. Prefer adding a new function or file over changing existing behaviour in a completed slice without documenting it.

---

## 3. VIBE CODING RULES

- Always explain the plan before writing code.
- Always list which files will be created or modified.
- Include a module-level docstring on every file and a docstring on every function.
- Include inline comments on non-obvious logic.
- Never hardcode secrets; always use config or environment variables.
- Never use magic numbers; use named constants or values from config.

---

## 4. ERROR HANDLING STANDARDS

- Wrap all external API calls in try/except. Log the exception and either re-raise or return a safe default (e.g. empty list).
- Wrap all database operations in try/except. Log the exception and re-raise or return a safe default as appropriate.
- Log all errors with timestamp, function name, and error text (use the logging module).
- Never crash the scheduler on a single job or pipeline failure; catch exceptions in the scheduled job and log them.

---

## 5. TESTING STANDARDS

- Every slice must have a UAT checklist before it is considered done (see SLICE_PLAN.md).
- Every function must be testable in isolation (no hidden global state that cannot be overridden for tests).
- `test_connections.py` must pass before any slice begins (required for Slice 0). Do not skip or weaken connection tests.

---

## 6. LOGGING STANDARDS

- Use the Python `logging` module only; never use `print` in production code (tests may use print for PASS/FAIL output).
- Use INFO for normal operations, WARNING for recoverable issues, ERROR for failures.
- All logs go to `logs/agent.log`. Use a single file handler; daily rotation is preferred (e.g. TimedRotatingFileHandler).
- Do not log API keys, tokens, or any secret.

---

## 7. SECURITY STANDARDS

- `.env` is never committed. Only `.env.example` (with placeholders and comments) is in the repo.
- No secrets in code, comments, or logs.
- All HTTP requests must use `timeout=10` (or a named constant) to avoid hanging.

---

## 8. DATABASE STANDARDS

- Always use parameterised queries (e.g. `?` placeholders); never build SQL with string formatting or f-strings for user or external data.
- Always close connections after use (use the context manager from `database/db.py`).
- Document schema changes in ARCHITECTURE.md.
