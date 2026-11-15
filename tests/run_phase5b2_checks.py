"""Run only Phase 5B2 synthetic checks with inherited offline/data denials."""
import json
import os
from pathlib import Path
import sys
import unittest
from tests.run_phase4c_regression import OfflineGuard, ROOT


class ProbeGuard(OfflineGuard):
    def check_path(self, value, writing=False):
        if not isinstance(value, int):
            path = Path(os.path.realpath(os.fsdecode(value)))
            if not writing and path in {ROOT/'pine/Phase5B1_C01_Decision_Probe_UNVALIDATED.pine', ROOT/'pine/Phase5B2_Selected_Candidate_Probe_UNVALIDATED.pine'}:
                return
        super().check_path(value, writing)


if __name__ == '__main__':
    guard = ProbeGuard()
    sys.addaudithook(guard.audit)
    from tools.verify_research_freeze import verify_environment
    verify_environment(json.loads((ROOT/'research_freeze/v0.2.2/environment.json').read_text()))
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(name) for name in ('tests.test_phase5b2_filters', 'tests.test_phase5b1_c01'))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    print(json.dumps({'passed':result.testsRun-len(result.errors)-len(result.failures)-len(result.skipped),
                      'failed':len(result.failures),'errored':len(result.errors),'skipped':len(result.skipped),
                      'guard_violations':guard.blocked,'environment':'MATCH_FROZEN_RECORD',
                      'pine_compile':'UNVERIFIED','pine_runtime':'UNVERIFIED'},sort_keys=True))
    sys.exit(0 if result.wasSuccessful() and not result.skipped and not guard.blocked else 1)
