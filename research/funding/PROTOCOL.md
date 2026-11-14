# Phase 4A — historical Funding and settlement Mark evidence

This package implements acquisition and data validation only. The authoritative contracts are the unchanged `STRATEGY_SPEC_v0.2.2.md` sections 7.3, 8.3.1 and 9.0.3 and the frozen official configuration. It never imports a position engine, opens the Stage-0B private ledger, applies Funding to trades or evaluates performance. The explicit Phase 4A request authorizes this data substage without changing the historical execution-authority wording in the frozen configuration.

## Access and provenance

Only unauthenticated GET requests to `https://api.bybit.com/v5/market/funding/history` and `/v5/market/mark-price-kline` are supported, with `category=linear`, `symbol=BTCUSDT`, and Mark `interval=1`. No API keys, credentials, account endpoints, current-instrument requests, alternate hosts or redirects are used. Each HTTP attempt is authorized before transport. Returned timestamps and identity are authorized before rate/price validation or caching the response body. An unauthorized response retains only its hash/status, not its contents.

Settlements belong to exactly one annual partition: `[2023-01-01,2024-01-01)` or `[2024-01-01,2025-01-01)`. Requests always contain explicit inclusive remote bounds inside that partition. No 2025+ data or Holdout access exists in this package. Mark minutes must be linked to observed settlements, minute aligned and wholly within global Development `[2023-01-01,2025-01-01)`. Only consecutive necessary minutes can share a request; a batch may not span unrelated minutes. The minimum prior minute for the 2023 start settlement is unauthorized and remains unavailable. The minute before the 2024 start is in authorized 2023; the 2025 boundary settlement itself is unauthorized. No warm-up exception is introduced.

Caller authorization, manifest identity and request provenance are checked before cache market-data files are read. Every file has an exact SHA-256, expected filename and ordinary nonsymlink path. Export validation happens before creating snapshot paths. The CLI accepts no year, symbol, range, parameter or endpoint overrides.

## Funding pagination and historical completeness

Funding requests use a maximum of 200 rows, with explicit start/end timestamps. Pages may be reverse ordered; rows are normalized by timestamp. The next inclusive end is one millisecond before the oldest returned timestamp. A short nonempty page does not stop traversal: the loader continues until it reaches the annual start or queries an explicitly bounded empty remainder. Identical duplicates are counted and deduplicated; conflicting or invalid copies quarantine the timestamp. Out-of-page overlaps fail closed and cannot silently advance the cursor or be cached. Partial observations survive later network failures with an incomplete scan status.

An independent scan of disjoint 14-day windows, itself paginated when needed, compares normalized timestamps and rates with the annual traversal. This can detect pagination loss, instability or mismatches. It cannot independently prove the historical settlement schedule. The maximum of 20,000 raw observations per scan and 8,192 HTTP attempts per execution are resource guards, never trading thresholds; exhaustion is explicitly incomplete.

Coverage is deliberately separated into: observed valid settlements, completion of the explicit API traversal, agreement with the re-query, and independently established historical calendar coverage. Current instrument metadata does not prove a historical interval. The retained interval histogram, modal cadence, irregular intervals and suspected internal gaps are derived solely from the actual authorized historical responses. Suspected gaps are diagnostics, not synthetic records. A constant cadence or an empty response alone cannot establish the absence of omitted settlements. Boundary first/last observations are retained. Actual missing-record counts remain UNKNOWN without complete dated calendar or interval-change evidence. This implementation does not promote those observations to DATA_READY when that prerequisite is absent.

## Mark validation and proxy

For each authorized observed settlement `t`, the only requested candle is `[t-60000,t)`. Contiguous required candles may be batched up to the documented 1,000-row maximum. The response must have the exact five string fields: minute start and positive finite OHLC values. Geometry, UTC minute alignment, completed status, duplicates, conflicts and exact linkage to `t` are checked. No forward fill, interpolation, zero substitution, trade-price substitution or later-period repair is supported. Raw invalid authorized responses are preserved for diagnosis, while invalid prices never enter normalized datasets.

The stored classification is `APPROXIMATE_MARK_PREVIOUS_1M_CLOSE`. Close supplies the registered proxy; the same minute's Low and High are retained separately for future sensitivity calculations. Neither an exact settlement tick nor guaranteed bounds is claimed. Missing Funding leaves the true denominator of required Mark minutes unknown, even if the count of requestable observed minutes is zero.

## Event classification and gates

An observed timestamp off a 15-minute boundary is `FUNDING_ALIGNMENT_UNRESOLVED`; no intrabar exit order is inferred. Timestamp-only tests establish that prior-bar exits reduce old exposure before Funding, entry at the same Open is exempt, and an old exit at that Open is a FUNDING_TIE with the frozen base and alternate precedence. Annual start has no carried position; annual end is excluded before Funding/Open/signal processing. These are classification contracts, not a position or cashflow simulation.

Data status is BLOCKED when no usable observations can be acquired, or PARTIAL_DATA when observations exist but any necessary completeness/alignment evidence remains unresolved. Snapshot-integrity PASS proves the retained bytes and access rules; it never overrides a partial/blocked data verdict. Full net-research validity remains outside Phase 4A, including later exposure-specific Funding application, sensitivity runs and execution verification. TradingView gates remain OPEN / UNVERIFIED.

## Execution, immutability and reproducibility

HTTP requests have 15-second timeouts, at most three attempts for retryable failures and a shared minimum 0.15-second interval between starts, with at most six concurrent Mark requests. HTTP 403 is terminal and opens a shared circuit: no alternate route or second-year retry bypasses it. HTTP 429 and bounded transient failures back off; unknown schema/API failures stop the request. Response sizes are bounded, and error bodies are hashed without retaining their contents. These guards are separate from trading parameters.

Each run creates an exclusive UTC version directory under ignored `data/funding/v0.2.2/<run-id>/<year>/`. Authorized raw HTTP responses, normalized Funding and Mark data, request logs and manifests are never overwritten. Public `reports/funding/v0.2.2/<run-id>/` contains only non-sensitive provenance, hashes, coverage/quality, missing reasons and test/verification evidence. File-level hashes support exact local cache verification. Normalized decimal strings are canonicalized without floating-point rounding; identical observations yield identical dataset hashes regardless of source ordering or equivalent decimal formatting. Volatile retrieval times and API server metadata legitimately change raw-response hashes across acquisitions.

The frozen design/research annotated tag objects, original tracked files and Stage-0B artifacts must remain byte-identical to starting commit `fd573b3d3b6f35f796defa74d2cbde00957f503c`. Only the related Git exclusion can change among those tracked paths. The original pinned numerical environment is verified before execution, although this data-only package uses decimal validation and no random sampling.

```
sh tools/research_python.sh -m unittest discover -s tests -v
sh tools/research_python.sh -m research.funding acquire
sh tools/research_python.sh -m research.funding verify <run-id>
```

Acquisition returns exit status 2 for PARTIAL_DATA/BLOCKED so automation cannot treat incomplete evidence as ready. Offline verification can succeed for a faithful blocked or partial snapshot and reports its unchanged data verdict explicitly. Reproduction requires the ignored snapshot and the unchanged frozen environment; no remote retrieval is performed by `verify`.

Official documentation checked for this implementation:

- [Funding history](https://bybit-exchange.github.io/docs/v5/market/history-fund-rate)
- [Mark price kline](https://bybit-exchange.github.io/docs/v5/market/mark-kline)
- [Rate limit rules](https://bybit-exchange.github.io/docs/v5/rate-limit)

The documentation describes endpoint limits and formats, not historical availability, an independently dated 2023/2024 schedule, or successful acquisition results. Those results must come from the actual run evidence.
