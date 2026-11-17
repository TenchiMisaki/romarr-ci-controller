"""Probe safety and classification tests; no candidate or Docker execution."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from platform_runtime import (AttestationVerifier,DockerProbe,private_environment,
    windows_pytest,windows_exe_smoke)
from platform_receipts import PlatformRejected
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


if __name__=='__main__':unittest.main()
