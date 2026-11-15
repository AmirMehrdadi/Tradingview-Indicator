"""Guarded fixture tests for the additive adapter and directly reused contracts."""
import argparse
import json
import sys
import tempfile
import os
import time
import unittest
from tests.run_phase4c_regression import OfflineGuard, ROOT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--focused',action='store_true');args=parser.parse_args()
    guard=OfflineGuard();original=os.getcwd()
    with tempfile.TemporaryDirectory(prefix='funding-attribution-tests-') as temp:
        os.chdir(temp);sys.addaudithook(guard.audit)
        from tools.verify_research_freeze import verify_environment
        verify_environment(json.loads((ROOT/'research_freeze/v0.2.2/environment.json').read_text()))
        modules=['tests.test_funding_attribution']
        if not args.focused:
            modules += ['tests.test_funding_lifecycle','tests.test_funding', 'tests.test_stage0b.LifecycleTests']
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in modules)
        start=time.monotonic();result=unittest.TextTestRunner(verbosity=2,stream=sys.stdout).run(suite)
        summary={'modules':modules,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
                 'failed':len(result.failures),'errored':len(result.errors),'skipped':len(result.skipped),
                 'elapsed_seconds':round(time.monotonic()-start,6),'guard_violations':guard.blocked,
                 'environment':'MATCH_FROZEN_RECORD','historical_regression':'NOT_RUN',
                 'selection':'DEPENDENCY_SCOPED_FIXTURES_ONLY_NO_PINE_OR_REAL_CACHE_TESTS'}
        print('FUNDING_ATTRIBUTION_TEST_SUMMARY='+json.dumps(summary,sort_keys=True))
        os.chdir(original)
        return 0 if result.wasSuccessful() and not result.skipped and not guard.blocked else 1


if __name__=='__main__':sys.exit(main())
