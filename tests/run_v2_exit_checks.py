"""One scoped synthetic regression; never run a historical engine in tests."""
import argparse,json,sys,tempfile,os,time,unittest
from tests.run_phase4c_regression import OfflineGuard,ROOT


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--focused',action='store_true');args=parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='v2-exit-fixtures-') as temp:
        original=os.getcwd();os.chdir(temp);guard=OfflineGuard();sys.addaudithook(guard.audit)
        from tools.verify_research_freeze import verify_environment
        verify_environment(json.loads((ROOT/'research_freeze/v0.2.2/environment.json').read_text()))
        modules=['tests.test_v2_exits']
        if not args.focused:modules+=['tests.test_funding_attribution','tests.test_funding_lifecycle','tests.test_funding','tests.test_stage0b.LifecycleTests']
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(m) for m in modules)
        start=time.monotonic();r=unittest.TextTestRunner(verbosity=2,stream=sys.stdout).run(suite)
        print('V2_EXIT_TEST_SUMMARY='+json.dumps(dict(modules=modules,passed=r.testsRun-len(r.failures)-len(r.errors)-len(r.skipped),failed=len(r.failures),errored=len(r.errors),skipped=len(r.skipped),elapsed_seconds=round(time.monotonic()-start,6),guard_violations=guard.blocked,environment='MATCH_FROZEN_RECORD'),sort_keys=True))
        os.chdir(original);return 0 if r.wasSuccessful() and not r.skipped and not guard.blocked else 1


if __name__=='__main__':sys.exit(main())
