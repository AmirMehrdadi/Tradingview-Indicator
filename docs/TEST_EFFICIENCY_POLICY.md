# Test efficiency policy

This engineering workflow applies to future phases. It changes no frozen strategy,
research parameter, access restriction or validation gate.

1. Identify the changed component, its dependencies and concrete risks before
   choosing checks.
2. Reuse existing tests first. Add coverage only for a genuinely uncovered behavior,
   boundary, invariant or regression.
3. Never duplicate tests merely to increase a pass count. Prefer a small number of
   meaningful regressions over superficially different assertions.
4. During development, run targeted checks for the change and its direct risks.
5. Before a publication-ready phase gate, run the applicable comprehensive offline
   regression once after the final code edit. If it fails, fix and rerun; disclose
   every additional execution. Do not rerun it just for reporting or packaging.
6. Do not rerun unaffected expensive suites without an identified dependency or
   reason. Record deliberately unexecuted tests and why they are out of scope.
7. Never omit mandatory safety, integrity, frozen-rule or protected-data gates.
   Keep the authorized environment and deny-by-default guard active.
8. Reuse existing references, runners and fixtures. Do not build another engine,
   runner or framework when the existing infrastructure is sufficient.
9. Report separately: new tests, reused tests, actual test executions and elapsed
   times. State timing scope, known overlapping coverage and intentional reruns.
   Do not sum repeated executions into a claimed count of distinct tests.
10. Distinguish synthetic Python checks, Pine static checks and genuine authorized
    TradingView execution evidence. A static PASS is not compilation/runtime proof.

For Phase 5C, development source checks use:

```
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5c_checks --focused
```

The unchanged full-suite selection is the same command without `--focused`.
This policy grants no permission for historical data, TradingView access or push.
