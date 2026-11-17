"""Typed receipt, provenance, leakage, stale-source and readiness regressions."""
from dataclasses import replace
import hashlib
import io
import json
import struct
import unittest
import zipfile

from platform_receipts import (ExpectedPlatform, PlatformRejected, canonical,
    read_bundle, verify_platform, readiness)


class PlatformReceiptTests(unittest.TestCase):
    """Real verifier code with independently supplied synthetic API snapshots."""

    def setUp(self):
        """Create a packaged Docker receipt with separate expected identities."""
        self.expected = ExpectedPlatform('docker-standard', 'example/source', 'a'*40,
            'b'*40, 'c'*40, 'example/builder', 'd'*40, '.github/workflows/build.yml',
            100, 1, 200, 'Image runtime proof', ('Boot candidate', 'Upload sanitized proof'),
            300, 'e'*64, 'f'*64, 'runtime-smoke')
        self.receipt = dict(schema='romarr-platform-receipt-v1', platform='docker-standard',
            source_repo='example/source', source_sha='a'*40, base_sha='b'*40,
            controller_sha='c'*40, producer_repo='example/builder', producer_sha='d'*40,
            workflow='.github/workflows/build.yml', run_id=100, attempt=1, job_id=200,
            scope='runtime-smoke', subject_sha256='f'*64,
            dimensions=dict.fromkeys(('build','environment','startup','test','collection','provenance','freshness'), 'PASS'),
            counts=dict(passed=2, failed=0, errors=0, skipped=0))
        self.cases = dict(schema='romarr-platform-cases-v1', cases=[
            dict(ordinal=1, outcome='passed'), dict(ordinal=2, outcome='passed')])
        self.source = dict(repo='example/source', head='a'*40, base='b'*40)

    def bundle(self, *, extra=None):
        """Build an actual canonical three-member ZIP and independently hash it."""
        content = {'receipt.json': canonical(self.receipt), 'cases.json': canonical(self.cases)}
        manifest = dict(schema='romarr-platform-manifest-v1', files={
            k: hashlib.sha256(v).hexdigest() for k,v in content.items()})
        content['manifest.json'] = canonical(manifest)
        if extra: content.update(extra)
        out = io.BytesIO()
        with zipfile.ZipFile(out,'w') as archive:
            for name,data in content.items(): archive.writestr(name,data)
        raw = out.getvalue()
        return raw, hashlib.sha256(raw).hexdigest()

    def evidence(self):
        """Create fresh separate GitHub metadata, bound to the archive digest."""
        raw,digest = self.bundle()
        e = replace(self.expected, artifact_sha256=digest)
        run = dict(id=100, run_attempt=1, repository=dict(full_name='example/builder'),
            head_sha='d'*40, path=e.workflow, status='completed', conclusion='success',
            html_url='https://github.com/example/builder/actions/runs/100')
        job = dict(id=200, run_id=100, run_attempt=1, name=e.job_name,
            head_sha='d'*40, status='completed', conclusion='success', steps=[
                dict(name=name,status='completed',conclusion='success') for name in e.required_steps])
        artifact = dict(id=300,expired=False,size_in_bytes=len(raw),digest='sha256:'+digest,
            workflow_run=dict(id=100,head_sha='d'*40))
        return e,dict(raw=raw,run=run,jobs=dict(total_count=1,jobs=[job]),artifact=artifact,
                      source_before=self.source,source_after=dict(self.source))

    def verified(self):
        """Model a separately authenticated external attestation verifier."""
        e,args = self.evidence()
        return verify_platform(e, **args, verify_subject=lambda x: (x.source_repo,x.source_sha,x.subject_sha256))

    def test_valid_packaged_receipt_stays_advisory(self):
        result = self.verified()
        self.assertEqual(result.state,'ADVISORY_VERIFIED')
        self.assertFalse(result.release_authorized)
        self.assertFalse(result.unattended_enabled)

    def test_self_reported_provenance_pass_is_not_accepted(self):
        e,args = self.evidence()
        result = verify_platform(e,**args)
        self.assertEqual(result.state,'ADVISORY_BLOCKED')
        self.assertEqual(result.dimensions['provenance'],'BLOCKED')

    def test_attestation_for_wrong_source_or_subject_rejected(self):
        e,args = self.evidence()
        for proof in [('foreign/repo','a'*40,'f'*64),('example/source','b'*40,'f'*64),('example/source','a'*40,'e'*64)]:
            with self.assertRaises(PlatformRejected):
                verify_platform(e,**args,verify_subject=lambda x: proof)

    def test_stale_source_or_base_rejected(self):
        for key in ('repo','head','base'):
            e,args=self.evidence();args['source_after']=dict(self.source,**{key:'changed'})
            with self.assertRaises(PlatformRejected): verify_platform(e,**args)

    def test_remote_run_job_and_artifact_mismatches_rejected(self):
        for section,field,value in [('run','id',True),('run','head_sha','e'*40),
            ('run','conclusion','failure'),('artifact','expired',True),('artifact','digest','wrong')]:
            e,args=self.evidence();args[section][field]=value
            with self.assertRaises(PlatformRejected):verify_platform(e,**args)

    def test_incomplete_job_collection_and_skipped_required_step_rejected(self):
        e,args=self.evidence();args['jobs']['total_count']=2
        with self.assertRaises(PlatformRejected):verify_platform(e,**args)
        e,args=self.evidence();args['jobs']['jobs'][0]['steps'][0]['conclusion']='skipped'
        with self.assertRaises(PlatformRejected):verify_platform(e,**args)

    def test_receipt_extra_secret_path_or_log_fields_rejected(self):
        for field in ('token','private_path','stdout','traceback'):
            self.setUp();self.receipt[field]='prohibited synthetic content'
            e,args=self.evidence()
            with self.assertRaises(PlatformRejected):verify_platform(e,**args)

    def test_case_names_and_nonordinal_ids_rejected(self):
        self.cases['cases'][0]['name']='private synthetic test name'
        e,args=self.evidence()
        with self.assertRaises(PlatformRejected):verify_platform(e,**args)
        self.setUp();self.cases['cases'][0]['ordinal']=True
        e,args=self.evidence()
        with self.assertRaises(PlatformRejected):verify_platform(e,**args)

    def test_count_mismatch_and_skip_cannot_be_green(self):
        for outcome in ('failed','errors','skipped'):
            self.setUp();self.cases['cases'][0]['outcome']=outcome
            self.receipt['counts'].update(passed=1,**{outcome:1})
            e,args=self.evidence()
            with self.assertRaises(PlatformRejected):verify_platform(e,**args)

    def test_raw_logs_extra_members_and_wrong_zip_digest_rejected(self):
        raw,digest=self.bundle(extra={'raw.log':b'private synthetic output'})
        with self.assertRaises(PlatformRejected):read_bundle(raw,digest)
        raw,digest=self.bundle()
        with self.assertRaises(PlatformRejected):read_bundle(raw,'0'*64)

    def test_future_android_not_silently_supported(self):
        with self.assertRaises(PlatformRejected):replace(self.expected,platform='android')

    def test_hidden_zip_comments_and_trailing_content_rejected(self):
        raw,digest=self.bundle()
        trailing=raw+b'private synthetic trailing content'
        with self.assertRaises(PlatformRejected):read_bundle(trailing,hashlib.sha256(trailing).hexdigest())
        out=io.BytesIO(raw)
        with zipfile.ZipFile(out,'a') as archive:archive.comment=b'private synthetic metadata'
        commented=out.getvalue()
        with self.assertRaises(PlatformRejected):read_bundle(commented,hashlib.sha256(commented).hexdigest())

    def test_local_only_extra_and_padding_cannot_hide_private_bytes(self):
        raw, _ = self.bundle()
        # Insert a local-only field; adjust every subsequent offset and EOCD so
        # ordinary zipfile still reads all three unmodified JSON members.
        length = struct.unpack_from('<H', raw, 26)[0]
        at = 30+length
        hidden = b'\xfe\xca\x04\x00hide'
        altered = bytearray(raw[:at]+hidden+raw[at:])
        struct.pack_into('<H', altered, 28, len(hidden))
        central = struct.unpack_from('<I', raw, len(raw)-6)[0]+len(hidden)
        pos = central
        for index in range(3):
            if index:
                offset = struct.unpack_from('<I', altered, pos+42)[0]
                struct.pack_into('<I', altered, pos+42, offset+len(hidden))
            name, extra, comment = struct.unpack_from('<3H', altered, pos+28)
            pos += 46+name+extra+comment
        struct.pack_into('<I', altered, len(altered)-6, central)
        with zipfile.ZipFile(io.BytesIO(altered)) as archive:
            self.assertFalse(archive.infolist()[0].extra)
            self.assertEqual(archive.read('receipt.json'), canonical(self.receipt))
        with self.assertRaises(PlatformRejected):
            read_bundle(bytes(altered), hashlib.sha256(altered).hexdigest())

    def test_collection_failure_is_never_upgraded_by_valid_case_counts(self):
        for state in ('COLLECTION_FAILED', 'INCOMPLETE', 'NOT_TESTED', 'FAIL'):
            self.receipt['dimensions']['collection'] = state
            result = self.verified()
            self.assertEqual(result.dimensions['collection'], state)
            self.assertEqual(result.state, 'ADVISORY_BLOCKED')

    def test_cross_platform_failure_dimensions_remain_separate(self):
        self.receipt['dimensions']['environment']='UNSUPPORTED'
        self.receipt['dimensions']['test']='NOT_TESTED'
        self.receipt['counts'].update(passed=0)
        self.cases['cases']=[]
        e,args=self.evidence();result=verify_platform(e,**args)
        self.assertEqual(result.dimensions['environment'],'UNSUPPORTED')
        self.assertEqual(result.dimensions['test'],'NOT_TESTED')
        self.assertEqual(result.state,'ADVISORY_BLOCKED')

    def test_readiness_missing_optional_and_required_platforms(self):
        result=self.verified();identity=(result.source_repo,result.source_sha,result.base_sha,result.controller_sha)
        policy=dict(schema='romarr-platform-policy-v1',required=['docker-standard','windows-py311'],optional=['android'])
        aggregate=readiness(policy=policy,identity=identity,results=[result])
        self.assertEqual(aggregate['state'],'ADVISORY_INCOMPLETE')
        self.assertEqual(aggregate['platforms']['windows-py311'],'NOT_TESTED')
        self.assertEqual(aggregate['platforms']['android'],'NOT_TESTED')
        policy['required']=['docker-standard']
        self.assertEqual(readiness(policy=policy,identity=identity,results=[result])['state'],'ADVISORY_READY')

    def test_readiness_rejects_duplicates_mixed_revisions_and_unknown_policy(self):
        result=self.verified();identity=(result.source_repo,result.source_sha,result.base_sha,result.controller_sha)
        policy=dict(schema='romarr-platform-policy-v1',required=['docker-standard'],optional=[])
        with self.assertRaises(PlatformRejected):readiness(policy=policy,identity=identity,results=[result,result])
        with self.assertRaises(PlatformRejected):readiness(policy=policy,identity=identity,results=[replace(result,source_sha='b'*40)])


if __name__=='__main__':unittest.main()
