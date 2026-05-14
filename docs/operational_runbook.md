# TWIP Operational Runbook

Standing operational rules for the Texas Well Intelligence Platform.
Rules in this document apply to all CC sessions working in this repo.
CC reads this file when working on TWIP and follows the rules
documented here without requiring per-prompt restatement.

This document accumulates rules as they emerge. Each rule is dated
at the section heading. Rules are added, not removed — superseded
rules are marked as such with the date of supersession and a pointer
to the replacement rule.

---

## Standing Rule: Zero-Skip on Data Sources

**Added: 2026-05-12**

Every data source identified in the TWIP scoping documents
(docs/scoping/phase1_rrc_sources.md, docs/scoping/phase2_documents.md,
docs/scoping/phase3_external.md, and any successor scoping files)
gets a pipeline. No source is dropped on grounds of MVP triage,
geographic scoping, complexity, scale, or expected commercial value.

This rule applies to all three phases:

- **Phase 1 (RRC regulatory backbone):** All 16+ source categories
  identified in the Phase 1 scoping doc receive pipelines.
- **Phase 2 (document OCR):** All document sources identified for
  Phase 2 are scraped. OCR is applied where source documents are
  not already in machine-readable form.
- **Phase 3 (external sources):** All 22 sources identified in
  Phase 3 scoping (TX-specific and federal reuse) receive pipelines.

Suggestions to narrow scope ("start with top 5 sources," "Permian-only
to start," "skip low-priority sources for MVP") are rejected by
default. If a CC instance proposes triage in a future prompt response,
the owner rejects the proposal and reiterates the zero-skip rule.

The build philosophy mirrors CWIP: completeness as differentiation.
Every regulatory source that exists for Texas oil and gas wells is
captured in TWIP. Same standard applied to Texas as Colorado.

Phase 2's 132M+ page OCR scale is a sequencing question (which
sources first, which run in parallel) but is not a skip question.
Throughput is handled by the pipeline execution pattern below.

Marketing for TWIP remains held until TWIP has shippable data. All
public marketing is CWIP-only during the build phase.

---

## Standing Rule: Pipeline Execution Pattern

**Added: 2026-05-12 (mirrors CWIP operational_runbook.md commit c65abf4)**

All data ingestion, transformation, and analysis pipelines run as
detached background processes. CC's role is:

1. **WRITE** the pipeline code
2. **TEST** that it starts cleanly (verify it can connect to its
   source, acquire any auth, and begin writing output)
3. **LAUNCH** it as a detached background process
4. **MOVE ON** to the next task

CC does NOT:

- Wait for pipeline completion
- Poll for status
- Block on long-running pipelines
- Babysit individual pipeline progress
- Use foreground execution for anything expected to run >5 minutes

Pipelines write all status, errors, progress, and completion to log
files. Owner reviews logs when they choose to check on progress, not
during CC sessions.

### Detached launch pattern

```bash
# Linux/WSL:
nohup python scripts/ingestion/pipeline_x.py > logs/pipeline_x.log 2>&1 &

# Windows PowerShell:
Start-Process python -ArgumentList "scripts/ingestion/pipeline_x.py" `
  -RedirectStandardOutput "logs/pipeline_x.log" `
  -RedirectStandardError "logs/pipeline_x_err.log" `
  -WindowStyle Hidden
```

### Pipeline script requirements

Each pipeline script must:

- Log every step (start, source connection, batch progress, errors,
  completion) with timestamps to its log file
- Use atomic file writes (write to `.tmp`, rename on success) so
  partial output never corrupts production data
- Have a heartbeat line written every 1-5 minutes so owner can
  verify progress without parsing every log line
- Exit cleanly on completion with a clear `PIPELINE_COMPLETE` log
  line and exit code 0
- Exit with non-zero code and `PIPELINE_FAILED: <reason>` on error

### When CC writes a new pipeline

1. Test it with a small subset (limit rows, single date range) to
   verify it runs end-to-end
2. Confirm the log file format works (timestamps, heartbeat, exit
   markers)
3. Launch the full pipeline detached
4. Print the launch command, log file path, and expected runtime
   estimate
5. Continue to the next task

### When owner asks "is pipeline X done"

- CC reads the log file (`tail` or `grep` for `PIPELINE_COMPLETE` /
  `PIPELINE_FAILED`)
- Reports status from log content
- Does NOT re-launch or interrupt a running pipeline unless asked

### When pipelines fail mid-run

- Failure is captured in the log
- Owner decides recovery: re-run from scratch, resume from
  checkpoint, debug and re-launch
- CC does not auto-restart

### Scope

This rule applies to all TWIP pipeline work. No exceptions for
"this one will be quick" — quick pipelines either run fast enough
to be fine in foreground (<5 min) or use this pattern regardless.

---

## Source Acquisition: Browser Automation via Playwright

**Added: 2026-05-12**

RRC bulk data sources served through mft.rrc.texas.gov require
browser-based session handling. Standard HTTP clients cannot fetch
these directly. Pattern for all TWIP RRC sources served via MFT:

1. Build a Playwright fetcher script at
   `scripts/automation/fetch_<source_name>.py`
2. Firefox backend, headless by default
3. Navigate to the MFT link, capture the download event, save to
   canonical source path
4. Write `source_meta.json` sidecar with SHA-256 hash, download
   URL, download method, timestamp
5. The corresponding ingestion pipeline accepts `--source-file`
   arg and verifies the hash before parsing

This pattern generalizes to every MFT-served RRC source: well
registry, production data, permits, completions, plugging records,
injection, pipeline permits, others.

No manual download steps are acceptable in TWIP operational
workflows. If a Playwright fetcher cannot navigate a source's
portal, the next attempts in priority order are:
(a) cookie-replay using a one-time manually-captured session token
(b) the RRC's official data request channels for an alternative
    endpoint
(c) other browser-automation approaches

Manual-download is not a documented pattern.

---

## Standing Rule: Documentation Required Per Ingestion

**Added: 2026-05-13**

Every ingestion prompt (P-TWIP-XXX for any source) MUST produce or
update the following documentation as part of its work:

1. **Source inventory entry** in `docs/source_inventory.md`
2. **Data dictionary entry** in `docs/data_dictionary.md`: full
   column-by-column schema for every output table
3. **QA companion table** at
   `data/raw/twip_qa_<table_slug>/twip_qa_<table_slug>.parquet`:
   Level 1 ingestion validation results
4. **Buyer-facing bundle manifest update** in
   `docs/delivery_bundle_manifest.md` for any new delivery table

Ingestion prompts that omit these are incomplete.

---

## QA Summary Review Pattern

**Added: 2026-05-14**

After any ingestion pipeline completes, or on a periodic schedule:

1. Run `python scripts/qa/run_qa_summary.py`
2. The runner scans all `twip_qa_*.parquet` companion tables
3. Writes `data/raw/twip_qa_summary/twip_qa_summary.parquet` with latest
   status per (table, check)
4. Generates `logs/qa_review_queue_<YYYYMMDD>.md` listing new FAILs and WARNs
5. Owner reviews the queue file and decides remediation

Level 1 FAILs are pipeline-blocking (the pipeline itself won't commit output).
Level 2/3 FAILs appear in the review queue for owner judgment.

See `docs/qa_framework.md` for the full three-level check pattern.

---

## Future Rules

Additional standing rules will be appended below as they emerge from
TWIP build work. Rules added here apply prospectively from their
date of addition.
