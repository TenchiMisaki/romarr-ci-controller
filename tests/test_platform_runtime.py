"""Probe safety and classification tests; no candidate or Docker execution."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from platform_runtime import (AttestationVerifier,DockerProbe,private_environment,
    windows_pytest,windows_exe_smoke,command,native_process)
from platform_receipts import PlatformRejected,verify_platform
import test_platform_receipts


class RuntimeTests(unittest.TestCase):
    """Use actual private fixtures and mocked process boundaries."""

    def setUp(self):
        """Create a disposable runner context without any real credential."""
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.env=dict(GITHUB_ACTIONS='true',RUNNER_OS='Linux',
            GITHUB_REPOSITORY='TenchiMisaki/romarr-ci-controller',RUNNER_TEMP=str(self.root),
            PATH='synthetic',SystemRoot=str(self.root),GH_TOKEN='synthetic-secret',
            SSH_AUTH_SOCK='synthetic-agent',PYTHONPATH='synthetic-hook')
        self.image='ghcr.io/blizzhacker/romarr@sha256:'+'a'*64

    def docker(self,*,bad_health=False,bad_dependencies=False,foreign=False):
        """Provide realistic inspect rows while observing every command."""
        calls=[];name=[None]
        def run(args,**kwargs):
            """Model local Docker boundaries without contacting a daemon."""
            self.assertNotIn('GH_TOKEN',kwargs['env'])
            calls.append(args);parts=args[3:]
            if parts[0]=='version':return 0,b'linux/amd64\n'
            if parts[:2]==['image','inspect']:
                return 0,json.dumps([dict(Id='sha256:'+'b'*64,RepoDigests=[self.image])]).encode()
            if parts[0]=='run':
                name[0]=parts[parts.index('--name')+1];return 0,b'container-id'
            if parts[:2]==['container','inspect']:
                row=dict(Image='sha256:'+'b'*64,Config=dict(User='1000:1000',
                    Labels={'romarr.controller.probe':'foreign' if foreign else name[0]}),
                    HostConfig=dict(NetworkMode='none',ReadonlyRootfs=True,Privileged=False))
                return 0,json.dumps([row]).encode()
            if parts[:2]==['container','rm']:return 0,b'removed'
            if parts[0]=='exec':
                if 'HEALTH_OK' in parts[-1]:return (1,b'') if bad_health else (0,b'HEALTH_OK\n')
                return (1,b'') if bad_dependencies else (0,b'DEPENDENCIES_OK\n')
            raise AssertionError(args)
        return run,calls

    def test_child_environment_excludes_secrets_agents_and_command_files(self):
        clean=private_environment(self.env)
        self.assertNotIn('GH_TOKEN',clean);self.assertNotIn('SSH_AUTH_SOCK',clean)
        self.assertNotIn('PYTHONPATH',clean)

    def test_docker_three_stable_passes_isolation_and_owned_cleanup(self):
        run,calls=self.docker();progress=[]
        result=DockerProbe(run=run,sleep=lambda n:None,progress=progress.append,environ=self.env).smoke(image=self.image)
        self.assertEqual(result,dict(environment='PASS',startup='PASS',test='PASS',provenance='BLOCKED',cleanup='PASS'))
        self.assertEqual(len(progress),3)
        start=next(c for c in calls if c[3]=='run')
        self.assertIn('--read-only',start);self.assertNotIn('--publish',start);self.assertNotIn('--volume',start)
        self.assertEqual(start[start.index('--network')+1],'none')
        self.assertEqual(start[start.index('--pull')+1],'never')

    def test_health_timeout_is_startup_failure_not_source_test_failure(self):
        run,calls=self.docker(bad_health=True);delays=[]
        result=DockerProbe(run=run,sleep=delays.append,environ=self.env).smoke(image=self.image)
        self.assertEqual(result['startup'],'FAIL');self.assertEqual(result['test'],'NOT_TESTED')
        self.assertEqual(result['cleanup'],'PASS');self.assertEqual(len(delays),29)

    def test_missing_runtime_dependency_is_environment_failure(self):
        run,_=self.docker(bad_dependencies=True)
        result=DockerProbe(run=run,sleep=lambda n:None,environ=self.env).smoke(image=self.image,browser=True)
        self.assertEqual(result['environment'],'FAIL');self.assertEqual(result['test'],'NOT_TESTED')

    def test_foreign_container_never_removed(self):
        run,calls=self.docker(foreign=True)
        with self.assertRaises(PlatformRejected):DockerProbe(run=run,sleep=lambda n:None,environ=self.env).smoke(image=self.image)
        self.assertFalse(any(c[3:5]==['container','rm'] for c in calls))

    def test_local_host_and_moving_image_tags_rejected(self):
        run,calls=self.docker()
        for env,image in (({},self.image),(self.env,'ghcr.io/blizzhacker/romarr:latest')):
            with self.assertRaises(PlatformRejected):DockerProbe(run=run,environ=env).smoke(image=image)
        self.assertEqual(calls,[])

    def test_attestation_pins_binary_source_workflow_and_subject(self):
        fixture=test_platform_receipts.PlatformReceiptTests();fixture.setUp();expected=fixture.expected
        binary=self.root/'gh';binary.write_bytes(b'verifier fixture')
        subject=self.root/'candidate';subject.write_bytes(b'candidate fixture')
        from dataclasses import replace
        expected=replace(expected,subject_sha256=hashlib.sha256(subject.read_bytes()).hexdigest())
        calls=[]
        def run(args,**kwargs):
            """Model a successful separately trusted cryptographic verifier."""
            calls.append((args,kwargs));return 0,b'[{"verified":"synthetic"}]'
        verifier=AttestationVerifier(binary,hashlib.sha256(binary.read_bytes()).hexdigest(),run=run,environ=self.env)
        proof=verifier.verify(expected,subject,read_token='synthetic-read-only')
        self.assertEqual(proof,(expected.source_repo,expected.source_sha,expected.subject_sha256))
        args,kwargs=calls[0]
        self.assertEqual(args[args.index('--source-digest')+1],expected.source_sha)
        self.assertEqual(args[args.index('--signer-digest')+1],expected.producer_sha)
        self.assertNotIn('synthetic-read-only',args)
        self.assertEqual(kwargs['env']['GH_TOKEN'],'synthetic-read-only')

    def test_missing_attestation_and_binary_drift_fail_closed(self):
        fixture=test_platform_receipts.PlatformReceiptTests();fixture.setUp();expected=fixture.expected
        binary=self.root/'gh';binary.write_bytes(b'verifier fixture')
        with self.assertRaises(PlatformRejected):AttestationVerifier(binary,'0'*64,environ=self.env)
        verifier=AttestationVerifier(binary,hashlib.sha256(binary.read_bytes()).hexdigest(),
            run=lambda *a,**k:(1,b'[]'),environ=self.env)
        with self.assertRaises(PlatformRejected):verifier.verify(expected,
            'oci://ghcr.io/example/source@sha256:'+'f'*64,read_token='synthetic')

    def windows_fixture(self):
        """Prepare distinct source, reports and interpreter paths."""
        env=dict(self.env,RUNNER_OS='Windows')
        source=self.root/'source';source.mkdir();private=self.root/'private';private.mkdir()
        exe=self.root/'python.exe';exe.write_bytes(b'fixture')
        return env,source,private,exe

    def test_windows_focused_suite_requires_exact_interpreter_and_clean_source(self):
        env,source,private,exe=self.windows_fixture();calls=[]
        def run(args,**kwargs):
            """Model real JUnit output without executing candidate source."""
            calls.append((args,kwargs));self.assertNotIn('GH_TOKEN',kwargs['env'])
            if 'rev-parse' in args:return 0,('a'*40).encode()
            if 'get-url' in args:return 0,b'https://github.com/example/source.git'
            if 'status' in args or 'ls-files' in args:return 0,b''
            if '-c' in args:return 0,b'3.11\n'
            (private/'junit.xml').write_text('<testsuite tests="1" errors="0" failures="0" skipped="0"><testcase name="private name"/></testsuite>')
            return 0,b'private stdout not returned'
        result=windows_pytest(executable=exe,source=source,source_repo='example/source',
            source_sha='a'*40,version='3.11',private=private,environ=env,run=run)
        self.assertEqual(result['test'],'PASS');self.assertEqual(result['cases'],[dict(ordinal=1,outcome='passed')])
        self.assertNotIn('private name',str(result))

    def test_windows_skips_produce_valid_blocked_receipt(self):
        env,source,private,exe=self.windows_fixture()
        def run(args, **kwargs):
            """Return a successful pytest invocation containing a real skip."""
            if 'rev-parse' in args:return 0,('a'*40).encode()
            if 'get-url' in args:return 0,b'https://github.com/example/source.git'
            if 'status' in args or 'ls-files' in args:return 0,b''
            if '-c' in args:return 0,b'3.11\n'
            (private/'junit.xml').write_text('<testsuite tests="1" errors="0" failures="0" skipped="1"><testcase name="private"><skipped/></testcase></testsuite>')
            return 0,b''
        result=windows_pytest(executable=exe,source=source,source_repo='example/source',
            source_sha='a'*40,version='3.11',private=private,environ=env,run=run)
        self.assertEqual(result['test'],'SKIPPED')
        fixture=test_platform_receipts.PlatformReceiptTests();fixture.setUp()
        from dataclasses import replace
        fixture.expected=replace(fixture.expected,platform='windows-py311',subject_sha256=None,scope='source-focused')
        fixture.receipt.update(platform='windows-py311',subject_sha256=None,scope='source-focused',counts=result['counts'])
        fixture.receipt['dimensions'].update(test=result['test'],collection=result['collection'])
        fixture.cases['cases']=result['cases']
        expected,evidence=fixture.evidence()
        verified=verify_platform(expected,**evidence,verify_subject=lambda e:(e.source_repo,e.source_sha,e.subject_sha256))
        self.assertEqual(verified.state,'ADVISORY_BLOCKED')
        self.assertEqual(verified.dimensions['test'],'SKIPPED')

    def test_native_executable_digest_checked_before_launch(self):
        env,source,private,exe=self.windows_fixture()
        with self.assertRaises(PlatformRejected):windows_exe_smoke(executable=exe,
            expected_sha256='0'*64,private=private,environ=env,run=lambda *a,**k:self.fail('launch'))

    def test_actual_executable_smoke_interface_not_packaging_exit(self):
        env,source,private,exe=self.windows_fixture()
        def run(args,**kwargs):
            """Create a valid proof through the actual EXE argument contract."""
            self.assertEqual(args[1],'--smoke-test');self.assertNotIn('GH_TOKEN',kwargs['env'])
            proof=Path(args[2]);proof.mkdir()
            fields=('nativeWindow','shellLayout','embeddedInterface','bundledPython','bundledHub',
                'pluginInstall','setupGuide','authentication','persistence','remoteView',
                'remoteDisconnectKeepsServer','versionIdentity','remoteSignInPolicy')
            (proof/'smoke-proof.json').write_text(json.dumps(dict.fromkeys(fields,True)))
            return 0,b''
        result=windows_exe_smoke(executable=exe,expected_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
            private=private,environ=env,run=run)
        self.assertEqual(result,dict(startup='PASS',test='PASS',provenance='BLOCKED'))


class ProcessTests(unittest.TestCase):
    """Real safe controller-owned processes, never ROMarr or prepared packages."""

    def test_both_pipes_drained_and_only_stdout_returned(self):
        rc, raw = command([sys.executable,'-c',
            "import os;os.write(1,b'a'*200000);os.write(2,b'b'*200000)"], env=dict(os.environ),timeout=10)
        self.assertEqual(rc,0);self.assertEqual(raw,b'a'*200000)

    def test_live_noisy_streams_are_stopped_without_disk_spooling(self):
        for stream in (1,2):
            start=time.monotonic()
            with self.assertRaisesRegex(PlatformRejected,'OUTPUT_BOUND'):
                command([sys.executable,'-c',
                    f"import os;\nwhile True: os.write({stream},b'x'*65536)"],env=dict(os.environ),timeout=10)
            self.assertLess(time.monotonic()-start,8)

    def test_exit_race_still_checks_final_output_and_nonzero_exit(self):
        with self.assertRaisesRegex(PlatformRejected,'OUTPUT_BOUND'):
            command([sys.executable,'-c',"import os;os.write(1,b'x'*1048577)"],env=dict(os.environ),timeout=10)
        self.assertEqual(command([sys.executable,'-c','raise SystemExit(7)'],env=dict(os.environ)),(7,b''))

    def test_deadline_and_missing_executable_fail_closed(self):
        with self.assertRaisesRegex(PlatformRejected,'TIMEOUT'):
            command([sys.executable,'-c','import time;time.sleep(10)'],env=dict(os.environ),timeout=.2)
        with self.assertRaises(PlatformRejected):
            command(['unavailable-controller-fixture-986263.exe'],env=dict(os.environ))

    @unittest.skipUnless(os.name=='nt','Windows Job Object acceptance requires Windows')
    def test_successful_launcher_exit_terminates_surviving_child(self):
        with tempfile.TemporaryDirectory() as private:
            ready=Path(private)/'ready'
            child="import os,time;from pathlib import Path;Path("+repr(str(ready))+").write_text(str(os.getpid()));time.sleep(60)"
            parent="import subprocess,sys,time;from pathlib import Path;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);\nwhile not Path("+repr(str(ready))+").exists(): time.sleep(.01)"
            self.assertEqual(native_process([sys.executable,'-c',parent],env=dict(os.environ),timeout=10),(0,b''))
            self.assert_pid_stopped(int(ready.read_text()))

    @unittest.skipUnless(os.name=='nt','Windows Job Object acceptance requires Windows')
    def test_timeout_terminates_owned_child(self):
        with tempfile.TemporaryDirectory() as private:
            ready=Path(private)/'ready'
            child="import os,time;from pathlib import Path;Path("+repr(str(ready))+").write_text(str(os.getpid()));time.sleep(60)"
            parent="import subprocess,sys,time;subprocess.Popen([sys.executable,'-c',"+repr(child)+"]);time.sleep(60)"
            with self.assertRaisesRegex(PlatformRejected,'NATIVE_SMOKE_TIMEOUT'):
                native_process([sys.executable,'-c',parent],env=dict(os.environ),timeout=2)
            self.assert_pid_stopped(int(ready.read_text()))

    @unittest.skipUnless(os.name=='nt','Windows Job Object acceptance requires Windows')
    def test_assignment_failure_never_runs_application(self):
        from platform_windows import OwnedWindowsProcess
        original=OwnedWindowsProcess._bind
        def deny_assignment(process):
            """Deny the actual OS assignment after real suspended creation."""
            original(process)
            process._api.AssignProcessToJobObject=lambda *args:False
        with tempfile.TemporaryDirectory() as private:
            marker=Path(private)/'must-not-exist'
            with patch.object(OwnedWindowsProcess,'_bind',deny_assignment):
                with self.assertRaises(PlatformRejected):
                    native_process([sys.executable,'-c',"from pathlib import Path;Path("+repr(str(marker))+").touch()"],env=dict(os.environ),timeout=5)
            self.assertFalse(marker.exists())

    def assert_pid_stopped(self,pid):
        """Observe the fixture PID without ever terminating by PID or name."""
        import ctypes
        from ctypes import wintypes
        api=ctypes.WinDLL('kernel32',use_last_error=True)
        api.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
        api.OpenProcess.restype=wintypes.HANDLE
        api.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
        api.WaitForSingleObject.restype=wintypes.DWORD
        api.CloseHandle.argtypes=[wintypes.HANDLE]
        handle=api.OpenProcess(0x100000,False,pid)
        if not handle:
            self.assertEqual(ctypes.get_last_error(),87)
            return
        # Job accounting can reach zero just before the process object becomes
        # signaled; bound and observe actual termination rather than racing it.
        try:self.assertEqual(api.WaitForSingleObject(handle,5000),0)
        finally:api.CloseHandle(handle)


if __name__=='__main__':unittest.main()
