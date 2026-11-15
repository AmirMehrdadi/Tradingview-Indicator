"""Guarded synthetic/reference/static runner. Does not execute or compile Pine."""
import json
import sys
import unittest
from tests.run_phase5b3_checks import FixtureGuard, ROOT

if __name__=='__main__':
    guard=FixtureGuard();sys.addaudithook(guard.audit)
    from tools.verify_research_freeze import verify_environment
    verify_environment(json.loads((ROOT/'research_freeze/v0.2.2/environment.json').read_text()))
    modules=['tests.test_phase5b3_pine','tests.test_phase5b3_state','tests.test_phase5b3_integration',
             'tests.test_phase5b2_filters','tests.test_phase5b1_c01']
    suites=[unittest.defaultTestLoader.loadTestsFromName(m) for m in modules]
    counts={m:s.countTestCases() for m,s in zip(modules,suites)}
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
    summary={'modules':counts,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
             'failed':len(result.failures),'errored':len(result.errors),'skipped':len(result.skipped),
             'guard_violations':guard.blocked,'environment':'MATCH_FROZEN_RECORD',
             'pine_execution':'NOT_ATTEMPTED','evidence':'PYTHON_REFERENCE_AND_STATIC_ONLY'}
    print('PHASE5B3_PINE_TEST_SUMMARY='+json.dumps(summary,sort_keys=True))
    sys.exit(0 if result.wasSuccessful() and not result.skipped and not guard.blocked else 1)
