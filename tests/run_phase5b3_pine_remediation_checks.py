"""Explicit guarded synthetic allowlist; optional original-source red tests only."""
import argparse,json,subprocess,sys,unittest
from tests.run_phase5b3_checks import FixtureGuard,ROOT

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--original-source-red',action='store_true');args=parser.parse_args()
    guard=FixtureGuard();sys.addaudithook(guard.audit)
    from tools.verify_research_freeze import verify_environment
    verify_environment(json.loads((ROOT/'research_freeze/v0.2.2/environment.json').read_text()))
    from tests import test_phase5b3_pine_remediation as review
    if args.original_source_red:
        review.SOURCE_OVERRIDE=subprocess.check_output(['git','show',review.ORIGINAL+':'+review.PINE]).decode()
        names=['tests.test_phase5b3_pine_remediation.RemediationSourceTests.test_six_component_identity_contract',
               'tests.test_phase5b3_pine_remediation.RemediationSourceTests.test_complete_audit_contract']
    else:
        names=['tests.test_phase5b3_pine_remediation','tests.test_phase5b3_pine','tests.test_phase5b3_state',
               'tests.test_phase5b3_integration','tests.test_phase5b2_filters','tests.test_phase5b1_c01']
    suites=[unittest.defaultTestLoader.loadTestsFromName(m) for m in names]
    counts={m:s.countTestCases() for m,s in zip(names,suites)}
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(suites))
    summary={'mode':'ORIGINAL_SOURCE_EXPECTED_RED' if args.original_source_red else 'CORRECTED_FULL_SYNTHETIC',
             'modules':counts,'passed':result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
             'failed':len(result.failures),'errored':len(result.errors),'skipped':len(result.skipped),
             'guard_violations':guard.blocked,'environment':'MATCH_FROZEN_RECORD','pine_execution':'NOT_ATTEMPTED'}
    print('PHASE5B3_PINE_REMEDIATION_SUMMARY='+json.dumps(summary,sort_keys=True))
    sys.exit(0 if result.wasSuccessful() and not result.skipped and not guard.blocked else 1)
