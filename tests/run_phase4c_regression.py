"""Test-only offline discovery. Exactly two user-approved historical-cache skips.

No production execution adapter. Unknown prohibited access aborts the entire run;
it is never converted into another skip or an expected test failure.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
APPROVED_SKIPS = {
    "tests.test_research_freeze.ResearchFreezeTests.test_all_evidence_verified_with_network_connections_disabled":
        "User-approved skip: freeze.verify_all reads and replays real Stage-0A caches; fixture-only restriction.",
    "tests.test_stage0b.FeatureAndGuardTests.test_all_data_hashes_checked_before_any_price_parsing":
        "User-approved skip: preflight reads real Stage-0A manifests/CSV bytes before injected hash rejection; fixture-only restriction.",
}


class ProhibitedAccess(KeyboardInterrupt):
    """Bypass unittest's ordinary exception handling: abort, never silently skip."""


class OfflineGuard:
    def __init__(self):
        self.blocked = []
        self.opens_checked = 0
        self.subprocesses_checked = 0

    def deny(self, reason):
        self.blocked.append(reason)
        raise ProhibitedAccess(reason)

    def check_path(self, value, writing=False):
        if isinstance(value, int):
            return  # Existing stdout/stderr and anonymous temporary descriptors.
        name = os.fsdecode(value)
        lexical = Path(os.path.abspath(name))
        resolved = Path(os.path.realpath(name))
        for path in (lexical, resolved):
            if path == ROOT / "data" or ROOT / "data" in path.parents:
                self.deny("REAL_REPOSITORY_DATA_ACCESS_DENIED")
            if ROOT in path.parents:
                relative = path.relative_to(ROOT)
                if writing:
                    self.deny("REPOSITORY_WRITE_DURING_TESTS_DENIED")
                allowed = relative.parts[0] in {
                    "research", "tools", "tests", "configs", "research_freeze", "reports", "docs", ".venv",
                } or str(relative) in {"STRATEGY_SPEC_v0.2.2.md", "requirements-research.lock", "requirements.txt",
                                       "README.md", "SPEC_CORRECTION_REPORT_v0.2.2_FA.md", ".gitignore"}
                if not allowed:
                    self.deny("UNREGISTERED_REPOSITORY_FILE_ACCESS_DENIED:"+str(relative))

    def audit(self, event, args):
        if event == "open":
            self.opens_checked += 1
            mode, flags = args[1], args[2]
            writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
                isinstance(flags, int) and bool(flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC)))
            self.check_path(args[0], writing)
        elif event in {"os.listdir", "os.scandir"}:
            self.check_path(args[0] if args else ".")
        elif event.startswith("socket."):
            # Socket construction is permitted for mocks; no DNS or traffic.
            if event != "socket.__new__":
                self.deny("NETWORK_ACCESS_DENIED")
        elif event == "subprocess.Popen":
            self.subprocesses_checked += 1
            executable, command, cwd, env = args
            command = list(command) if isinstance(command, (tuple, list)) else []
            binary = Path(os.fsdecode(executable)).name
            safe_git = binary == "git" and len(command) > 1 and command[1] in {
                "rev-parse", "show", "cat-file", "merge-base", "ls-tree",
            }
            safe_uname = binary == "uname" and command[1:] == ["-p"]
            safe_python_file = binary == "file" and len(command) == 3 and command[1] == "-b" and Path(command[2]).resolve() in {
                Path(sys.executable).resolve(), Path(sys._base_executable).resolve(),
            }
            if not (safe_git or safe_uname or safe_python_file):
                self.deny("NON_ALLOWLISTED_SUBPROCESS_DENIED:"+binary)
            if safe_git and any("data/" in str(arg) or "stage0b_private" in str(arg) for arg in command):
                self.deny("GIT_DATA_ACCESS_DENIED")
        elif event in {"os.system", "os.exec", "os.posix_spawn", "os.posix_spawnp"}:
            self.deny("UNGUARDED_PROCESS_EXECUTION_DENIED")


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


class ApprovedSkip(unittest.TestCase):
    def __init__(self, test_id, reason):
        super().__init__("runTest")
        self.test_id, self.reason = test_id, reason

    def id(self):
        return self.test_id

    def __str__(self):
        return self.test_id

    def runTest(self):
        self.skipTest(self.reason)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--focused", action="store_true", help="Run only all new lifecycle fixtures under the same guards")
    mode.add_argument("--replay-hashes", action="store_true", help="Hash two identical in-memory replays of each scenario; do not export ledgers")
    args = parser.parse_args()
    # Directory-descriptor cleanup in old synthetic tests opens names such as
    # 'data' relative to temporary fds. Keep cwd outside the repository so the
    # audit event (which omits dir_fd) cannot confuse these with real caches.
    temporary_cwd = tempfile.TemporaryDirectory(prefix="phase4c-tests-")
    original_cwd = os.getcwd()
    os.chdir(temporary_cwd.name)
    guard = OfflineGuard()
    sys.addaudithook(guard.audit)
    try:
        if args.replay_hashes:
            from tests.test_funding_lifecycle import fixture_replay_hashes
            print(json.dumps(fixture_replay_hashes(), sort_keys=True, indent=2))
            return 0
        loader = unittest.TestLoader()
        found = list(cases(loader.discover(str(ROOT / "tests"), pattern="test_funding_lifecycle.py" if args.focused else "test*.py", top_level_dir=str(ROOT))))
        seen = {case.id() for case in found}
        if not args.focused and not set(APPROVED_SKIPS) <= seen:
            raise RuntimeError("APPROVED_SKIP_IDS_NOT_FOUND_ABORT")
        suite = unittest.TestSuite(ApprovedSkip(case.id(), APPROVED_SKIPS[case.id()]) if case.id() in APPROVED_SKIPS else case for case in found)
        result = unittest.TextTestRunner(verbosity=2, stream=sys.stdout).run(suite)
        counts = {"discovered": len(found), "executed_or_skipped": result.testsRun,
                  "passed": result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped),
                  "failed": len(result.failures), "errored": len(result.errors), "skipped": len(result.skipped),
                  "expected_failures": len(result.expectedFailures), "unexpected_successes": len(result.unexpectedSuccesses)}
        payload = {"mode": "focused" if args.focused else "guarded_regression", "counts": counts,
                   "skips": [{"id": case.id(), "reason": reason} for case, reason in result.skipped],
                   "full_historical_regression": "NOT FULLY RE-EXECUTED",
                   "real_data_or_network_violations": guard.blocked,
                   "file_open_audits": guard.opens_checked, "allowlisted_subprocess_audits": guard.subprocesses_checked}
        print("PHASE4C_TEST_SUMMARY="+json.dumps(payload, sort_keys=True))
        expected_skips = set() if args.focused else set(APPROVED_SKIPS)
        exact_skips = {case.id() for case, reason in result.skipped} == expected_skips
        return 0 if result.wasSuccessful() and not guard.blocked and exact_skips else 1
    except ProhibitedAccess as exc:
        print("BLOCKED: "+str(exc))
        return 2
    finally:
        os.chdir(original_cwd)
        temporary_cwd.cleanup()


if __name__ == "__main__":
    sys.exit(main())
