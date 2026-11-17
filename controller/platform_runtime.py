"""Dormant advisory probes of prepared artifacts, never release builders.

Only separately accepted disposable runners may call these probes. No workflow
or CLI invokes them automatically. Raw output stays private and is never returned
as a public diagnostic. Runtime observations do not authenticate build provenance.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid

from evidence import collect_junit
from platform_receipts import PlatformRejected, SHA40, SHA256, REPO


def file_digest(path):
    """Hash actual bytes incrementally, without interpreting an executable."""
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for chunk in iter(lambda: handle.read(131072), b''):
            h.update(chunk)
    return h.hexdigest()


def private_environment(environ):
    """Drop credentials, command files, agents, Git overrides and Python hooks."""
    return {key: environ[key] for key in (
        'PATH', 'SystemRoot', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP',
        'LANG', 'LC_ALL') if key in environ}


def command(args, *, env, cwd=None, timeout=30):
    """Run without a shell; retain bounded output privately with a deadline."""
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            process = subprocess.run(args, env=env, cwd=cwd, timeout=timeout,
                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, shell=False)
        except (OSError, subprocess.TimeoutExpired):
            raise PlatformRejected('PLATFORM_COMMAND_UNAVAILABLE_OR_TIMEOUT') from None
        if stdout.tell() > 1024*1024 or stderr.tell() > 1024*1024:
            raise PlatformRejected('PLATFORM_COMMAND_OUTPUT_BOUND')
        stdout.seek(0)
        return process.returncode, stdout.read()


def runner_gate(environ, os_name):
    """Require explicit disposable-runner context; never fall back to a host."""
    if (environ.get('GITHUB_ACTIONS') != 'true' or environ.get('RUNNER_OS') != os_name
            or environ.get('GITHUB_REPOSITORY') != 'TenchiMisaki/romarr-ci-controller'
            or not environ.get('RUNNER_TEMP')):
        raise PlatformRejected('DISPOSABLE_RUNNER_REQUIRED')
    root = Path(environ['RUNNER_TEMP']).resolve(strict=True)
    if not root.is_dir():
        raise PlatformRejected('RUNNER_TEMP_INVALID')
    return root


class AttestationVerifier:
    """Use a pinned GitHub CLI binary as the cryptographic verifier.

    Signed SLSA provenance is required, with exact repository, signer workflow,
    signer digest and source digest. No self-reported BUILD-INFO substitute.
    The separately trusted caller must bind package-vs-contained-EXE relations;
    verifying a ZIP does not independently attest an extracted executable.
    """

    def __init__(self, executable, executable_sha256, *, run=command, environ=None):
        self.executable = Path(executable).resolve(strict=True)
        if (type(executable_sha256) is not str or not SHA256.fullmatch(executable_sha256)
                or file_digest(self.executable) != executable_sha256):
            raise PlatformRejected('PROVENANCE_VERIFIER_BINARY_MISMATCH')
        self.run, self.environ = run, dict(os.environ if environ is None else environ)
        self.executable_sha256 = executable_sha256

    def verify(self, expected, subject, *, read_token):
        """Verify exact artifact bytes or digest-pinned OCI subject independently."""
        if expected.subject_sha256 is None or type(read_token) is not str or not read_token:
            raise PlatformRejected('ATTESTATION_EXPECTATION_INVALID')
        if file_digest(self.executable) != self.executable_sha256:
            raise PlatformRejected('PROVENANCE_VERIFIER_BINARY_CHANGED')
        if str(subject).startswith('oci://'):
            if not re.fullmatch(r'oci://ghcr\.io/[a-z0-9_.-]+/[a-z0-9_.-]+@sha256:' + expected.subject_sha256, str(subject)):
                raise PlatformRejected('ATTESTATION_OCI_SUBJECT_INVALID')
            target = str(subject)
        else:
            path = Path(subject).resolve(strict=True)
            if not path.is_file() or file_digest(path) != expected.subject_sha256:
                raise PlatformRejected('ATTESTATION_FILE_DIGEST_MISMATCH')
            target = str(path)
        env = private_environment(self.environ)
        # This process verifies bytes; it never executes the subject. The token
        # is restricted to the trusted verifier, absent from runtime probes.
        env['GH_TOKEN'] = read_token
        env['GH_PROMPT_DISABLED'] = '1'
        args = [str(self.executable), 'attestation', 'verify', target,
            '--repo', expected.source_repo, '--signer-repo', expected.producer_repo,
            '--signer-workflow', expected.producer_repo + '/' + expected.workflow,
            '--signer-digest', expected.producer_sha, '--source-digest', expected.source_sha,
            '--predicate-type', 'https://slsa.dev/provenance/v1', '--format', 'json', '--limit', '10']
        rc, raw = self.run(args, env=env, timeout=60)
        if file_digest(self.executable) != self.executable_sha256:
            raise PlatformRejected('PROVENANCE_VERIFIER_BINARY_CHANGED')
        try:
            proof = json.loads(raw)
        except (ValueError, UnicodeError):
            raise PlatformRejected('ATTESTATION_OUTPUT_INVALID') from None
        if rc != 0 or type(proof) is not list or not 1 <= len(proof) <= 10 or any(type(p) is not dict or not p for p in proof):
            raise PlatformRejected('ATTESTATION_NOT_VERIFIED')
        return expected.source_repo, expected.source_sha, expected.subject_sha256


class DockerProbe:
    """Observe a prepared digest-pinned image in an isolated Linux runner.

    No pull, build, push, host bind, socket mount, network, registry login or
    production target is permitted. Uses a fixed local Docker socket explicitly.
    """

    def __init__(self, *, run=command, sleep=time.sleep, progress=None, environ=None):
        self.run, self.sleep = run, sleep
        self.progress = progress or (lambda info: None)
        self.environ = dict(os.environ if environ is None else environ)

    def smoke(self, *, image, browser=False):
        """Require three health passes; always clean up only the owned container."""
        runner_gate(self.environ, 'Linux')
        if type(browser) is not bool or type(image) is not str or not re.fullmatch(
                r'ghcr\.io/(?:blizzhacker|tenchimisaki)/romarr@sha256:[0-9a-f]{64}', image):
            raise PlatformRejected('IMAGE_EXPECTATION_INVALID')
        env = private_environment(self.environ)
        name = 'romarr-advisory-' + uuid.uuid4().hex
        label = 'romarr.controller.probe=' + name
        result = dict(environment='NOT_TESTED', startup='NOT_TESTED', test='NOT_TESTED',
                      provenance='BLOCKED', cleanup='NOT_TESTED')
        with tempfile.TemporaryDirectory(dir=self.environ['RUNNER_TEMP']) as private:
            env['DOCKER_CONFIG'] = private
            prefix = ['docker', '--host', 'unix:///var/run/docker.sock']
            def docker(*args, timeout=30):
                """Use only explicit socket and credential-free command environment."""
                return self.run(prefix + list(args), env=env, timeout=timeout)
            rc, version = docker('version', '--format', '{{.Server.Os}}/{{.Server.Arch}}')
            if rc or version.strip() not in {b'linux/amd64', b'linux/arm64'}:
                raise PlatformRejected('DOCKER_ENVIRONMENT_UNSUPPORTED')
            rc, raw = docker('image', 'inspect', image)
            try:
                images = json.loads(raw)
                identity = images[0]['Id']
                if rc or len(images) != 1 or image not in images[0]['RepoDigests'] or not re.fullmatch('sha256:[0-9a-f]{64}', identity):
                    raise ValueError()
            except (ValueError, KeyError, TypeError, IndexError):
                raise PlatformRejected('PREPARED_IMAGE_IDENTITY_UNVERIFIED') from None
            result['environment'] = 'PASS'
            attempted = False
            try:
                attempted = True
                rc, _ = docker('run', '--detach', '--name', name, '--label', label,
                    '--pull', 'never', '--network', 'none', '--read-only', '--user', '1000:1000',
                    '--cap-drop', 'ALL', '--security-opt', 'no-new-privileges', '--pids-limit', '128',
                    '--memory', '512m', '--cpus', '1', '--log-driver', 'none',
                    '--tmpfs', '/config:rw,noexec,nosuid,size=64m,uid=1000,gid=1000,mode=0700',
                    '--tmpfs', '/tmp:rw,noexec,nosuid,size=32m,uid=1000,gid=1000,mode=0700', image)
                if rc:
                    result['startup'] = 'FAIL'
                    return result
                rc, raw = docker('container', 'inspect', name)
                rows = json.loads(raw)
                container = rows[0]
                if (rc or len(rows) != 1 or container['Image'] != identity
                        or container['Config']['Labels'].get('romarr.controller.probe') != name
                        or container['HostConfig']['NetworkMode'] != 'none'
                        or container['HostConfig']['ReadonlyRootfs'] is not True
                        or container['HostConfig']['Privileged'] is not False
                        or container['Config']['User'] != '1000:1000'):
                    raise PlatformRejected('RUNNING_IMAGE_OR_ISOLATION_MISMATCH')
                consecutive = 0
                health = "import json,urllib.request; r=urllib.request.urlopen('http://127.0.0.1:6868/api/health',timeout=1); d=json.load(r); assert r.status==200 and d=={'ok':True}; print('HEALTH_OK')"
                for attempt in range(1, 31):
                    rc, raw = docker('exec', name, 'python', '-c', health, timeout=5)
                    consecutive = consecutive + 1 if rc == 0 and raw.strip() == b'HEALTH_OK' else 0
                    self.progress(dict(phase='HEALTH', attempt=attempt, limit=30,
                                       interval=2, stable=consecutive, required=3))
                    if consecutive == 3:
                        break
                    if attempt < 30:
                        self.sleep(2)
                if consecutive != 3:
                    result['startup'] = 'FAIL'
                    return result
                result['startup'] = 'PASS'
                dependencies = "import os,shutil,requests,rom_hub; assert os.geteuid()==1000; assert shutil.which('bsdtar') and shutil.which('git'); p='/config/controller-permission-proof'; open(p,'x').close(); os.unlink(p); print('DEPENDENCIES_OK')"
                if browser:
                    dependencies = "import playwright; from romarr.library import rar_tool; assert rar_tool().kind=='unar'; " + dependencies
                rc, raw = docker('exec', name, 'python', '-c', dependencies)
                result['environment'] = 'PASS' if rc == 0 and raw.strip() == b'DEPENDENCIES_OK' else 'FAIL'
                result['test'] = 'PASS' if result['environment'] == 'PASS' else 'NOT_TESTED'
                return result
            finally:
                if attempted:
                    rc, raw = docker('container', 'inspect', name)
                    try:
                        owned = json.loads(raw)
                        matches = rc == 0 and len(owned) == 1 and owned[0]['Config']['Labels'].get('romarr.controller.probe') == name
                    except (ValueError, KeyError, TypeError, IndexError):
                        matches = False
                    if matches:
                        cleanup_rc, _ = docker('container', 'rm', '--force', name)
                        result['cleanup'] = 'PASS' if cleanup_rc == 0 else 'FAIL'
                    else:
                        result['cleanup'] = 'BLOCKED'


def windows_pytest(*, executable, source, source_repo, source_sha, version,
                   private, environ=None, run=command):
    """Run a fixed focused source suite in a disposable Windows runner.

    Dependencies must already be prepared. No installation, canonical checkout
    mutation, private fixtures or network-marked tests. This is focused coverage,
    not full Windows application/runtime acceptance.
    """
    environ = dict(os.environ if environ is None else environ)
    root = runner_gate(environ, 'Windows')
    source, private, executable = (Path(p).resolve(strict=True) for p in (source, private, executable))
    if (version not in {'3.11', '3.13'} or not REPO.fullmatch(str(source_repo))
            or not SHA40.fullmatch(str(source_sha)) or not executable.is_file()
            or source == root or not source.is_relative_to(root) or not private.is_relative_to(root)
            or private.is_relative_to(source) or source.is_relative_to(private)):
        raise PlatformRejected('WINDOWS_SOURCE_OR_ENVIRONMENT_INVALID')
    env = private_environment(environ)
    for args, wanted in ((['git', '-C', str(source), 'rev-parse', 'HEAD'], source_sha),
                         (['git', '-C', str(source), 'remote', 'get-url', 'origin'], 'https://github.com/'+source_repo+'.git'),
                         (['git', '-C', str(source), 'status', '--porcelain', '--untracked-files=all'], ''),
                         (['git', '-C', str(source), 'ls-files', '--others', '--ignored', '--exclude-standard'], '')):
        rc, raw = run(args, env=env)
        if rc or raw.decode().strip() != wanted:
            raise PlatformRejected('WINDOWS_SOURCE_NOT_CLEAN_OR_PINNED')
    rc, raw = run([str(executable), '-I', '-c', "import sys;print(str(sys.version_info.major)+'.'+str(sys.version_info.minor));import pytest"], env=env)
    if rc or raw.decode().strip() != version:
        raise PlatformRejected('WINDOWS_TOOLCHAIN_UNAVAILABLE')
    junit = private/'junit.xml'
    if junit.exists():
        raise PlatformRejected('PRESERVE_PRIVATE_JUNIT')
    tests = ['tests/test_file_reports.py', 'tests/test_file_report_paths.py', 'tests/test_sidecars.py']
    rc, _ = run([str(executable), '-I', '-m', 'pytest', '-q', '-m', 'not network',
                 '--junitxml='+str(junit), *tests], env=env, cwd=str(source), timeout=180)
    if (not junit.is_file() or junit.is_symlink() or not junit.resolve().is_relative_to(private)
            or junit.stat().st_size > 8*1024*1024):
        raise PlatformRejected('WINDOWS_JUNIT_MISSING_OR_OVERSIZED')
    header = junit.read_bytes()
    if b'<!DOCTYPE' in header or b'<!ENTITY' in header:
        raise PlatformRejected('WINDOWS_JUNIT_UNSAFE')
    counts, anonymous = collect_junit(junit)
    return dict(environment='PASS', test='PASS' if rc == 0 and not counts['failed'] and not counts['errors'] else 'FAIL',
                collection='PASS', exit=rc, counts=counts,
                cases=[dict(ordinal=i, outcome=x['outcome']) for i,x in enumerate(anonymous,1)])


def native_process(args, *, env, timeout=180):
    """Launch an owned Windows EXE invisibly and bound its full process tree.

    Output files stay private. On timeout, taskkill targets only this still-owned
    process tree; do not fall back to killing by executable name.
    """
    if os.name != 'nt':
        raise PlatformRejected('NATIVE_WINDOWS_REQUIRED')
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        process = subprocess.Popen(args, env=env, stdin=subprocess.DEVNULL,
            stdout=stdout, stderr=stderr, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            if process.poll() is None:
                subprocess.run([str(Path(env['SystemRoot'])/'System32'/'taskkill.exe'),
                    '/PID', str(process.pid), '/T', '/F'], env=env,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                    creationflags=subprocess.CREATE_NO_WINDOW, check=False)
                process.wait(timeout=15)
            raise PlatformRejected('NATIVE_SMOKE_TIMEOUT') from None
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=15)
        return process.returncode, b''


def windows_exe_smoke(*, executable, expected_sha256, private, environ=None, run=native_process):
    """Launch actual prepared EXE bytes; return only fixed boolean observations."""
    environ = dict(os.environ if environ is None else environ)
    root = runner_gate(environ, 'Windows')
    executable, private = (Path(p).resolve(strict=True) for p in (executable, private))
    if (not executable.is_relative_to(root) or not private.is_relative_to(root)
            or executable.suffix.lower() != '.exe' or not executable.is_file()
            or not SHA256.fullmatch(str(expected_sha256)) or file_digest(executable) != expected_sha256
            or private == root or private == executable.parent or not environ.get('SystemRoot')):
        raise PlatformRejected('NATIVE_SUBJECT_OR_PRIVATE_PATH_INVALID')
    proof = private/'native-proof'
    if proof.exists():
        raise PlatformRejected('PRESERVE_NATIVE_PROOF')
    env = private_environment(environ)
    env['SystemRoot'] = environ['SystemRoot']
    env['PATH'] = str(Path(env['SystemRoot'])/'System32') + os.pathsep + env['SystemRoot']
    for key in ('TEMP', 'TMP', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA'):
        env[key] = str(private)
    rc, _ = run([str(executable), '--smoke-test', str(proof)], env=env, timeout=180)
    if rc:
        return dict(startup='FAIL', test='NOT_TESTED', provenance='BLOCKED')
    evidence = proof/'smoke-proof.json'
    if (not evidence.is_file() or evidence.is_symlink() or not evidence.resolve().is_relative_to(private)
            or evidence.stat().st_size > 1024*1024):
        raise PlatformRejected('NATIVE_PROOF_MISSING_OR_OVERSIZED')
    try:
        observed = json.loads(evidence.read_bytes())
    except (ValueError, UnicodeError):
        raise PlatformRejected('NATIVE_PROOF_INVALID') from None
    checks = ('nativeWindow', 'shellLayout', 'embeddedInterface', 'bundledPython',
              'bundledHub', 'pluginInstall', 'setupGuide', 'authentication', 'persistence',
              'remoteView', 'remoteDisconnectKeepsServer', 'versionIdentity', 'remoteSignInPolicy')
    if type(observed) is not dict or any(observed.get(k) is not True for k in checks):
        return dict(startup='PASS', test='FAIL', provenance='BLOCKED')
    return dict(startup='PASS', test='PASS', provenance='BLOCKED')
