# CLAUDE.md -- Standing Instructions for TWIP Sessions

## Project context

Texas Well Intelligence Platform (TWIP). State-level oil and gas regulatory
data product covering every well registered with the Texas Railroad Commission.
Sister product to CWIP (Colorado), located at
`D:\UE 2025 Work\colorado-well-intelligence-platform\`.

Pricing: $3,999/year per state. Separate subscription from CWIP.

Owner: Artem Kuryachy (Elareon Group LLC). Solo founder.

## Workflow (NON-NEGOTIABLE)

Three-party workflow:
- **Owner** = product manager, business owner, final decision maker
- **Assistant** (Claude in chat) = prompt engineer, drafts prompts for Claude
  Code to execute
- **Claude Code** (this instance) = executor, runs prompts, reports back

Owner does NOT execute changes directly except for manual things the assistant
explicitly delegates (manual file edits, PowerShell commands, Substack
publishing, RRC PDQ lookups, etc.).

Every flow: owner describes intent -> assistant drafts prompt -> owner pastes
into CC -> CC executes and reports -> owner pastes output back to assistant.

## Sub-agent usage (RESTRICTED)

Claude Code's sub-agent feature is restricted to read-only diagnostic tasks
only.

Acceptable sub-agent uses:
- Read-only inventories (list files, count rows, summarize existing content)
- Read-only classification (categorize files by type, group by attribute)
- Read-only lookups across multiple files

NOT acceptable for sub-agents:
- File creation of any kind (scripts, docs, configs, Parquet outputs)
- File modifications (edits to existing files)
- Pipeline implementation or execution
- Git operations (add, commit, push, branch)
- Any work whose output affects what gets shipped to buyers

For all file creation, modifications, and pipeline work, the main CC session
does the work directly. This keeps the reasoning visible to the owner and
makes verification possible.

If the main CC delegates work to a sub-agent and the sub-agent returns output
that includes file changes or pipeline state, the main CC must verify the
changes by reading the relevant files directly before treating them as
complete. Sub-agent output is advisory only for any non-read-only work.

## Standing rules

See `docs/operational_runbook.md` for:
- **Pipeline execution pattern** -- detached background processes, log-based
  status, no polling/babysitting. CC writes, tests, launches, moves on.
- **Zero-skip rule** -- every data source ingested, every field captured, no
  MVP triage, no geographic scoping, no "start with top 5" suggestions.
- **Source acquisition via Playwright** -- Firefox headless for RRC MFT portal.
  No manual download patterns. `scripts/automation/rrc_mft_fetcher.py` is the
  generic fetcher; per-source fetchers at `scripts/automation/fetch_*.py`.
- **Documentation requirement per ingestion** -- every ingestion prompt must
  update: source inventory, data dictionary, QA companion table, and delivery
  bundle manifest.
- **Unified QA framework** -- see `docs/qa_framework.md`. Three-level check
  pattern (L1 ingestion, L2 referential, L3 analytical). Per-table companion
  tables at `data/raw/twip_qa_<slug>/`. Level 1 fails block pipeline commit.
  Run via `scripts/qa/run_qa_for_table.py`.

## Architecture conventions

- Wells-as-backbone star schema (mirrors CWIP)
- `api10` = "42" + 8-digit RRC apinum (Texas state code + county + well)
- `operator_number` stored as `str` everywhere, verbatim from RRC source
- Table naming: `twip_{dim|fact|ref|qa}_{table_name}` prefix required
- Raw preservation layer (`twip_fact_*_raw`) retains every source row before
  any derived tables
- Atomic Parquet writes via `.tmp` + `os.replace()` -- no partial output
  corruption
- Source provenance via `source_meta.json` sidecars with SHA-256, download URL,
  timestamp
- Output location: `data/raw/{table_name}/{table_name}.parquet`
- Column classification rule: columns that vary in <1% of api10s with multiple
  source rows are WELL_PROPERTY (go to master); all others are EVENT_PROPERTY
  (go to fact tables)

See `docs/source_inventory.md` for source-by-source status.
See `docs/data_dictionary.md` for table and column documentation.
See `docs/qa_framework.md` for the three-level QA pattern.
See `docs/delivery_bundle_manifest.md` for buyer-facing product description.

## Protected scripts

Scripts that have shipped and require scoped lift per-prompt to modify:
- `scripts/automation/fetch_*.py` -- Playwright fetchers; modifying affects
  monthly source refresh
- `scripts/automation/rrc_mft_fetcher.py` -- generic MFT fetcher base
- `scripts/ingestion/ingest_*.py` -- per-source ingestion pipelines
- `scripts/ingestion/derive_*.py` -- derivation pipelines (operator history,
  well-lease crosswalk)
- `scripts/ingestion/build_*.py` -- crosswalk/linkage builders

Modifying a protected script requires the prompt to explicitly state:
"Protection LIFTED for this prompt only, scoped to [specific lines/function].
Resumes for subsequent prompts."

## Prompt format (STRICT)

Every prompt from the assistant includes:
1. Plain-English explanation FIRST, before any prompt block
2. Prompt block in fenced code with sequential numbering (`P-TWIP-NNN`); no
   number reused
3. Structured phases (`PHASE A`, `B`, `C`, etc.) for multi-step work
4. `ABSOLUTE CONSTRAINTS` section at the end

## Communication norms

- Owner curses freely; CC accepts tone and does not curse gratuitously
- Direct prose preferred over multiple-choice questioning
- Don't restate preferences back to owner
- Don't ask questions after drafting answers
- Verify-first on completion claims: if owner reports an issue after CC reports
  success, CC was wrong, not owner
- Don't suggest taking breaks or stopping unless explicitly asked
- No emojis unless owner uses them first

## Forensic verification rule

If two or more prompts have claimed to fix the same issue and the issue
persists, the next prompt MUST be a read-only forensic audit that:
- Prints verbatim source content
- Prints verbatim rendered output
- Prints verbatim deployed/S3 content if applicable
- Maps divergences across layers
- Recommends but does NOT execute the fix

The corrective prompt that follows is targeted to the specific divergence the
audit identified.

## Sister-product references

CWIP repo: `D:\UE 2025 Work\colorado-well-intelligence-platform\`
Cross-state architecture comparison: `docs/cross_state_comparison.md`

Documentation, schema, and QA patterns are intended to be uniform across CWIP
and TWIP except where technical nuance requires divergence:
- Texas EBCDIC + COMP-3 packed decimal production data
- Lease-level production reporting (vs well-level in Colorado)
- Dual-key system (api10 for wells, district+lease_number for production)
- RRC district structure (14 districts vs ECMC single-state)
- P-5 operator registry (standalone dimension vs embedded in well master)
