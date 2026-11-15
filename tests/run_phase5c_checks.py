"""Phase 5C offline synthetic/reference/static checks; no Pine runtime access."""
import json,sys,unittest
from tests.run_phase5b3_checks import FixtureGuard,ROOT

if __name__=='__main__':
    guard=FixtureGuard();sys.addaudithook(guard.audit)
    from tools.verify_research_freeze import verify_environment
    verify_environment(json.loads((ROOT/'research_freeze/v0.2.2/environment.json').read_text()))
    names=['tests.test_phase5c_signals','tests.test_phase5b3_pine_remediation','tests.test_phase5b3_pine',
           'tests.test_phase5b3_state','tests.test_phase5b3_integration','tests.test_phase5b2_filters','tests.test_phase5b1_c01',
           'tests.test_phase5a_temporal']
    suites=[unittest.defaultTestLoader.loadTestsFromName(name) for name in names]
    counts={name:suite.countTestCases() for name,suite in zip(names,suites)}
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
    summary={'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
             'failed':len(result.failures),'errored':len(result.errors),'skipped':len(result.skipped),
             'modules':counts,'guard_violations':guard.blocked,'environment':'MATCH_FROZEN_RECORD',
             'pine_execution':'NOT_ATTEMPTED','evidence':'SYNTHETIC_PYTHON_AND_SOURCE_STATIC_ONLY'}
    print('PHASE5C_TEST_SUMMARY='+json.dumps(summary,sort_keys=True))
    sys.exit(0 if result.wasSuccessful() and not result.skipped and not guard.blocked else 1)
