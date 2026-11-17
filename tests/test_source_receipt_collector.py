"""Ordered source-full collector with real envelopes and modeled HTTP/proof."""
import copy
from dataclasses import replace
import io
import json
import unittest

from source_receipt_collector import collect_source_receipt
from stage6_pr_identity_v32 import CONTROLLER_REPO, ExactPR, SOURCE_REPO
from stage6_pr_transport_v38 import ReadOnlyGitHubTransport
from test_controller_cycle import Ports
import test_platform_receipts as fixtures

API = 'https://api.github.com/repos/'


class SourceCollectorTests(unittest.TestCase):
    """Neither copied snapshots nor canonical artifact claims authenticate source."""

    def setUp(self):
        fixture = fixtures.PlatformReceiptTests()
        fixture.setUp()
        fixture.expected = replace(fixture.expected, platform='source-linux',
            source_repo=SOURCE_REPO, producer_repo=CONTROLLER_REPO, producer_sha='c'*40,
            subject_sha256=None, scope='source-full')
        fixture.receipt.update(platform='source-linux', source_repo=SOURCE_REPO,
            producer_repo=CONTROLLER_REPO, producer_sha='c'*40,
            subject_sha256=None, scope='source-full')
        self.expected, self.evidence = fixture.evidence()
        self.evidence['run'].update(repository=dict(full_name=CONTROLLER_REPO),
            head_sha='c'*40, html_url=f'https://github.com/{CONTROLLER_REPO}/actions/runs/100')
        self.evidence['jobs']['jobs'][0]['head_sha'] = 'c'*40
        self.evidence['artifact']['workflow_run']['head_sha'] = 'c'*40
        self.fixture = fixture
        self.source = ExactPR(42, 'a'*40, 'b'*40)
        ports = Ports()
        self.pr, self.branch = ports.pr, ports.branch
        self.calls, self.reads, self.faults = [], {}, {}
        self.after_download = self.after_proof = None

    def get_json(self, url):
        """Serve separately copied snapshots at exact known endpoints only."""
        self.calls.append(('GET', url))
        self.reads[url] = self.reads.get(url, 0)+1
        if url in self.faults:
            raise self.faults[url]
        if url == API+SOURCE_REPO+'/pulls/42': value = self.pr
        elif url == API+SOURCE_REPO+'/branches/main': value = self.branch
        elif url == API+CONTROLLER_REPO+'/actions/runs/100': value = self.evidence['run']
        elif url == API+CONTROLLER_REPO+'/actions/runs/100/jobs?per_page=100': value = self.evidence['jobs']
        elif url == API+CONTROLLER_REPO+'/actions/artifacts/300': value = self.evidence['artifact']
        else: raise AssertionError('Unexpected target')
        return copy.deepcopy(value)

    def download(self, url, limit, digest):
        """Verify callback contract; never provide credentials or real network."""
        self.calls.append(('DOWNLOAD', url))
        self.assertEqual(url, API+CONTROLLER_REPO+'/actions/artifacts/300/zip')
        self.assertEqual(limit, 4*1024*1024)
        self.assertEqual(digest, self.expected.artifact_sha256)
        if self.after_download: self.after_download()
        return self.evidence['raw']

    def proof(self, expected):
        """Model an independent execution-provenance verifier, not producer data."""
        self.calls.append(('PROOF', expected.source_sha))
        self.assertEqual(expected, self.expected)
        if self.after_proof: self.after_proof()
        return expected.source_repo, expected.source_sha, None

    def collect(self, **kwargs):
        """Run the production collector with all authority flags checked."""
        args = dict(expected=self.expected, source=self.source, get_json=self.get_json,
                    get_artifact_bytes=self.download, verify_execution=self.proof)
        args.update(kwargs)
        result = collect_source_receipt(**args)
        self.assertFalse(result.test_accepted)
        self.assertFalse(result.publication_authorized)
        self.assertFalse(result.unattended_enabled)
        return result

    def test_valid_full_receipt_order_and_final_reads(self):
        result = self.collect()
        self.assertEqual(result.state, 'ADVISORY_VERIFIED')
        kinds = [kind for kind, _ in self.calls]
        self.assertEqual(kinds, ['GET']*7+['DOWNLOAD','PROOF']+['GET']*5)
        self.assertEqual(self.calls[-2:], [('GET', API+SOURCE_REPO+'/pulls/42'),
                                         ('GET', API+SOURCE_REPO+'/branches/main')])
        self.assertEqual(self.reads[API+CONTROLLER_REPO+'/actions/artifacts/300'], 2)
        self.assertFalse(result.receipt.release_authorized)
        self.assertFalse(result.receipt.unattended_enabled)

    def test_focused_or_packaged_or_foreign_scope_rejected_before_network(self):
        for changes in ({'scope':'source-focused'}, {'source_repo':'foreign/repo'},
                {'producer_repo':'foreign/repo'}, {'producer_sha':'d'*40},
                {'source_sha':'d'*40}, {'platform':'windows-exe','subject_sha256':'f'*64}):
            with self.subTest(changes=changes):
                self.assertEqual(self.collect(expected=replace(self.expected,**changes)).state, 'BLOCKED')
                self.assertEqual(self.calls, [])

    def test_missing_independent_proof_stays_advisory_blocked(self):
        result = self.collect(verify_execution=None)
        self.assertEqual(result.state,'ADVISORY_BLOCKED')
        self.assertEqual(result.receipt.dimensions['provenance'],'BLOCKED')
        self.assertFalse(any(kind=='PROOF' for kind,_ in self.calls))

    def test_both_windows_source_receipt_identities_are_supported(self):
        for platform in ('windows-py311','windows-py313'):
            with self.subTest(platform=platform):
                self.fixture.expected=replace(self.fixture.expected,platform=platform)
                self.fixture.receipt['platform']=platform
                self.expected,generated=self.fixture.evidence()
                self.evidence['raw']=generated['raw']
                self.evidence['artifact'].update(size_in_bytes=len(generated['raw']),
                    digest='sha256:'+self.expected.artifact_sha256)
                result=self.collect()
                self.assertEqual(result.state,'ADVISORY_VERIFIED')
                self.assertEqual(result.receipt.platform,platform)

    def test_wrong_proof_does_not_authorize_artifact_claims(self):
        self.assertEqual(self.collect(verify_execution=lambda _: ('foreign/repo','a'*40,None)).state,'BLOCKED')

    def test_initial_stale_source_stops_before_download_or_proof(self):
        self.branch['commit']['sha'] = 'd'*40
        self.assertEqual(self.collect().state,'BLOCKED')
        self.assertEqual([kind for kind,_ in self.calls], ['GET','GET'])

    def test_source_move_during_download_or_proof_rejected(self):
        self.after_download = lambda: self.pr['head'].update(sha='d'*40)
        self.assertEqual(self.collect().state,'BLOCKED')
        self.setUp()
        self.after_proof = lambda: self.branch['commit'].update(sha='e'*40)
        self.assertEqual(self.collect().state,'BLOCKED')

    def test_artifact_expiry_after_download_or_proof_rejected(self):
        self.after_download = lambda: self.evidence['artifact'].update(expired=True)
        self.assertEqual(self.collect().state,'BLOCKED')
        self.setUp()
        self.after_proof = lambda: self.evidence['artifact'].update(expired=True)
        self.assertEqual(self.collect().state,'BLOCKED')

    def test_final_run_or_required_step_change_rejected(self):
        self.after_proof = lambda: self.evidence['run'].update(conclusion='failure')
        self.assertEqual(self.collect().state,'BLOCKED')
        self.setUp()
        self.after_proof = lambda: self.evidence['jobs']['jobs'][0]['steps'][0].update(conclusion='skipped')
        self.assertEqual(self.collect().state,'BLOCKED')

    def test_initial_metadata_failure_never_downloads(self):
        self.evidence['jobs']['total_count'] = 2
        self.assertEqual(self.collect().state,'BLOCKED')
        self.assertFalse(any(kind in {'DOWNLOAD','PROOF'} for kind,_ in self.calls))

    def test_download_digest_size_or_type_failure_never_invokes_proof(self):
        for raw in (b'corrupt', self.evidence['raw']+b'x', None):
            with self.subTest(raw=type(raw)):
                self.evidence['raw'] = raw
                self.assertEqual(self.collect().state,'BLOCKED')
                self.assertFalse(any(kind=='PROOF' for kind,_ in self.calls))
                self.calls.clear()

    def test_prohibited_archive_content_rejected_before_privileged_proof(self):
        self.fixture.receipt['private_path'] = 'synthetic prohibited content'
        self.expected, generated = self.fixture.evidence()
        self.evidence['raw'] = generated['raw']
        self.evidence['artifact'].update(size_in_bytes=len(generated['raw']),
                                        digest='sha256:'+self.expected.artifact_sha256)
        self.assertEqual(self.collect().state,'BLOCKED')
        self.assertFalse(any(kind=='PROOF' for kind,_ in self.calls))

    def test_callback_error_is_sanitized_and_not_retried(self):
        url=API+CONTROLLER_REPO+'/actions/artifacts/300'
        self.faults[url]=RuntimeError('private synthetic signed URL')
        result=self.collect()
        self.assertEqual(result.state,'BLOCKED')
        self.assertNotIn('private synthetic',str(result))
        self.assertEqual(self.reads[url],1)

    def test_provenance_error_does_not_emit_raw_error(self):
        def unavailable(_):
            raise OSError('private synthetic credential details')
        result=self.collect(verify_execution=unavailable)
        self.assertEqual(result.state,'BLOCKED')
        self.assertNotIn('private synthetic',str(result))

    def test_concrete_transport_accepts_large_full_bundle_without_storage_auth(self):
        self.fixture.receipt['counts']['passed'] = 2000
        self.fixture.cases['cases'] = [dict(ordinal=n,outcome='passed') for n in range(1,2001)]
        self.expected, generated = self.fixture.evidence()
        self.evidence['raw'] = generated['raw']
        self.evidence['artifact'].update(size_in_bytes=len(generated['raw']),
                                        digest='sha256:'+self.expected.artifact_sha256)
        self.assertGreater(len(generated['raw']),65536)
        case=self
        storage='https://abc.blob.core.windows.net/results/fixture.zip?sig=synthetic'
        requests=[]
        class Response(io.BytesIO):
            """Actual HTTP-reader contract, backed by bounded fixture bytes."""
            def __init__(self,status,body=b'',headers=None):
                super().__init__(body)
                self.status=status
                self.headers=headers or {'Content-Length':str(len(body))}
        class Opener:
            """Drive the real redirect/hash transport and metadata parser."""
            def open(self,request,timeout):
                requests.append(request)
                case.assertEqual(request.get_method(),'GET')
                if request.full_url==storage:
                    case.assertIsNone(request.get_header('Authorization'))
                    return Response(200,case.evidence['raw'])
                case.assertEqual(request.get_header('Authorization'),'Bearer synthetic-fixture')
                if request.full_url.endswith('/zip'):
                    return Response(302,headers={'Location':storage})
                return Response(200,json.dumps(case.get_json(request.full_url)).encode())
        transport=ReadOnlyGitHubTransport('synthetic-fixture',opener=Opener(),archive_limit=4*1024*1024)
        result=self.collect(get_json=transport.get_json,get_artifact_bytes=transport.get_artifact_bytes)
        self.assertEqual(result.state,'ADVISORY_VERIFIED')
        self.assertEqual(sum(r.full_url==storage for r in requests),1)
        requests.clear()
        default=ReadOnlyGitHubTransport('synthetic-fixture',opener=Opener())
        self.assertEqual(self.collect(get_json=default.get_json,get_artifact_bytes=default.get_artifact_bytes).state,'BLOCKED')
        self.assertFalse(any(r.full_url.endswith('/zip') or r.full_url==storage for r in requests))

    def test_archive_limit_is_explicit_bounded_and_never_boolean(self):
        for limit in (True,0,-1,4*1024*1024+1,None):
            with self.assertRaises(ValueError):
                ReadOnlyGitHubTransport('synthetic-fixture',archive_limit=limit)


if __name__ == '__main__':
    unittest.main()
