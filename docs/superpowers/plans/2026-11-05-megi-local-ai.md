# Megi Local AI Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task. User approved all implementation and requested immediate execution; execute inline without another approval round.

**Goal:** Train a local intent model and serve accurate tourism answers from the existing database.
**Architecture:** TF-IDF word/character features with logistic regression; independent date/entity parsing and database-backed response service; Flask integration and safe public chat controls.
**Tech Stack:** Python, scikit-learn, Flask, SQLAlchemy, unittest.
**Spec:** docs/ai/rancangan-pelatihan.md (approved in chat).

## Global Constraints

- Local training/inference; no paid AI API.
- Training and evaluation questions separated; report real metrics and errors.
- Date interpretation uses Asia/Jakarta.
- Do not invent times, verified sources, official status, or alter existing event dates.
- Public chat must not mutate records; require authenticated administrator for existing creation actions.

## Review Focus

- Ambiguous or repeated event names must prompt a choice with dates.
- Invalid dates and month/year transitions must not silently select unrelated events.
- Missing/corrupt model must return an actionable error without reverting to misleading old FAQ.
- Promo text must not claim discounts actually unsupported by booking calculation.
- Untrusted chat/database text must render as text, not executable HTML.

### Task 1: Train and evaluate the intent model
Files: backend/ai/intent_model.py, backend/ai/data/{train,test}.json, backend/train_ai.py, backend/ai/artifacts/*, backend/requirements.txt, backend/tests/test_ai_model.py.
Interface: predict_intent(message: str) -> dict with intent, confidence, model; train(output_dir: Path) -> dict metrics.
- [x] Add tests: disjoint normalized train/test questions; expected labels for core intents; saved model reload; evaluation counts match held-out set; missing artifact explicit failure.
- [x] Run unittest test_ai_model, observe failure before implementation.
- [x] Implement dataset, training pipeline, persisted artifact and report. Train once; report held-out results without tuning against that test set.
- [x] Run model tests, inspect evaluation including failures.

### Task 2: Ground answers and guard the endpoint
Files: backend/ai/dates.py, backend/ai/concierge.py, backend/app.py, backend/tests/test_chat_and_ticketing.py.
Interfaces: parse_period(message: str, today: date) -> tuple[date,date,str] | None (raises ValueError for invalid explicit date); answer_question(message: str, today: date | None = None) -> dict reply, intent, confidence, sources.
- [x] Write failing temporary-database tests for next-day schedules, past events, missing start time, ambiguous names, live ticket prices, promos, unknown entities, unsupported topics, invalid input, forbidden guest writes and unknown actions.
- [x] Observe failures using unittest, implement date/name retrieval and replies, integrate into existing route.
- [x] Run entire unittest suite, ensure no writes to live database.

### Task 3: Visitor experience and student handoff
Files: frontend/templates/layouts/base.html, frontend/js/main.js, docs/ai/panduan-tanya-megi.md, README.md.
Interface: askMegi(question: str) sends question-only request; escaped formatting for all chat text, same-origin source links built from structured sources.
- [x] Add tests for safe public shortcuts, removal of official claims, and source links in endpoint responses; verify failing behavior first.
- [x] Replace public creation buttons with questions, escape HTML, clarify application-data provenance and missing facts.
- [x] Document dataset, architecture, training commands, metrics and limitations; HTTP smoke test real running server with read-only questions.
- [x] Independent review, fix material findings, rerun full tests, verify live data unchanged.

## Execution ledger

- Setup: folder is not a Git repository; no worktree/commit possible. Work in requested project with pre-change source archive docs/backups/sebelum-training-megi-20261105.zip. Do not initialize Git or move running project.
- Spec approved; execution method selected inline to fulfill explicit request to implement now.

- Task 1: complete. Real local fit on 256 questions, held-out 64; accuracy 59/64, macro F1 0.906417. Persisted artifact and full prediction report. No held-out tuning.
- Task 2: complete. Test-first API/date/database checks; temporary in-memory database. Live conversation uses trained model and data queries.
- Task 3: complete. Visitor question shortcuts, escaped messages, restricted source URLs; Indonesian training/presentation guide and repeatable safe test runner.
- Review: independent read-only reviewer reported two Important findings, no Critical findings. Fixed in one pass: relative day/month parsing and numeric/unsupported date handling; grammar words wrongly treated as entities. Both have observed RED then GREEN regressions.
- Additional observed integration defect: WBL matched another Bahari destination. Fixed alias normalization after regression failed; now passes.
- Final verification: 27 Python tests (23 new, 4 existing), JavaScript rendering checks, JS syntax check, pip dependency check all pass. HTTP smoke: 13 checks with all returned source links HTTP 200. Database fingerprint unchanged across smoke requests (29 events, 21 destinations, 23 ticket types).
- Visual browser verification remains unavailable; no visual-layout completion claim. Native browser access previously timed out/minimized. HTTP/template and JavaScript behavior verified.
- Finish: no Git repository or branch exists; changes remain in the user-authorized project. Pre-change archive retained. No merge, push, or publication performed.
