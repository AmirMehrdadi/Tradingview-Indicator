"""Phase 5C offline synthetic/reference/static checks; no Pine runtime access."""
import argparse,json,sys,time,unittest
from tests.run_phase5b3_checks import FixtureGuard,ROOT

if __name__=='__main__':
    execution_started=time.perf_counter()
    parser=argparse.ArgumentParser(description=__doc__,epilog='Policy: docs/TEST_EFFICIENCY_POLICY.md')
    parser.add_argument('--focused',action='store_true',help='Run only Phase 5C source-contract checks.')
    args=parser.parse_args()
    guard=FixtureGuard();sys.addaudithook(guard.audit)
    from tools.verify_research_freeze import verify_environment
    verify_environment(json.loads((ROOT/'research_freeze/v0.2.2/environment.json').read_text()))
    names=['tests.test_phase5c_signals','tests.test_phase5b3_pine_remediation','tests.test_phase5b3_pine',
           'tests.test_phase5b3_state','tests.test_phase5b3_integration','tests.test_phase5b2_filters','tests.test_phase5b1_c01',
           'tests.test_phase5a_temporal']
    if args.focused:names=['tests.test_phase5c_signals.SourceContractTests']
    suites=[unittest.defaultTestLoader.loadTestsFromName(name) for name in names]
    counts={name:suite.countTestCases() for name,suite in zip(names,suites)}
    tests_started=time.perf_counter()
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
    test_elapsed=time.perf_counter()-tests_started
    summary={'mode':'FOCUSED_SOURCE' if args.focused else 'FULL_SYNTHETIC',
             'test_elapsed_seconds':round(test_elapsed,6),'execution_elapsed_seconds':round(time.perf_counter()-execution_started,6),
             'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
             'failed':len(result.failures),'errored':len(result.errors),'skipped':len(result.skipped),
             'modules':counts,'guard_violations':guard.blocked,'environment':'MATCH_FROZEN_RECORD',
             'pine_execution':'NOT_ATTEMPTED','evidence':'SYNTHETIC_PYTHON_AND_SOURCE_STATIC_ONLY'}
    print('PHASE5C_TEST_SUMMARY='+json.dumps(summary,sort_keys=True))
    sys.exit(0 if result.wasSuccessful() and not result.skipped and not guard.blocked else 1)
