"""Stage gates for synthetic fixtures only. No historical suite or market loader."""
import argparse
import io
import json
from pathlib import Path
import sys
import unittest
from tests.run_phase4c_regression import OfflineGuard, ROOT


class FixtureGuard(OfflineGuard):
    def check_path(self,value,writing=False):
        if not isinstance(value,int):
            path=Path(value).resolve()
            if not writing and (path==ROOT/'pine' or path.parent==ROOT/'pine' and path.suffix=='.pine'):return
        super().check_path(value,writing)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['A','B','all'],required=True);args=parser.parse_args()
    guard=FixtureGuard();sys.addaudithook(guard.audit)
    from tools.verify_research_freeze import verify_environment
    verify_environment(json.loads((ROOT/'research_freeze/v0.2.2/environment.json').read_text()))
    modules=['tests.test_phase5b3_state']
    if args.stage in ('B','all'):modules+=['tests.test_phase5b3_integration','tests.test_phase5b2_filters','tests.test_phase5b1_c01']
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in modules)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary={'stage':args.stage,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),'failed':len(result.failures),'errored':len(result.errors),'skipped':len(result.skipped),'guard_violations':guard.blocked,'environment':'MATCH_FROZEN_RECORD'}
    print('PHASE5B3_TEST_SUMMARY='+json.dumps(summary,sort_keys=True))
    sys.exit(0 if result.wasSuccessful() and not result.skipped and not guard.blocked else 1)
