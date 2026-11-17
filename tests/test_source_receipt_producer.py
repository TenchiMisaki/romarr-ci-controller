"""Real serializer/consumer round trips; no source execution or live provenance."""
from dataclasses import replace
import hashlib
import unittest

from platform_receipts import ExpectedPlatform, PlatformRejected, read_bundle, verify_platform
from source_receipt_producer import SourceRun, anonymous_cases, source_bundle
from stage6_pr_identity_v32 import CONTROLLER_REPO, SOURCE_REPO


def junit(body='<testcase name="private synthetic name"/>', *, tests=1, failures=0, errors=0, skipped=0):
    """Build private XML, preserving attributes and outputs the public ZIP must omit."""
    return (f'<testsuites><testsuite tests="{tests}" failures="{failures}" errors="{errors}" skipped="{skipped}">'
        + body + '</testsuite></testsuites>').encode()


class ProducerTests(unittest.TestCase):
    """The producer cannot grant provenance, freshness or unattended authority."""

    def setUp(self):
        self.identity = SourceRun('source-linux','a'*40,'b'*40,'c'*40,
            '.github/workflows/full.yml',100,1,200)

    def bundle(self, xml=None, **kwargs):
        """Use the actual source serializer with independently supplied expectations."""
        return source_bundle(self.identity, xml=junit() if xml is None else xml,
            pytest_exit=kwargs.get('pytest_exit',0),expected_cases=kwargs.get('expected_cases',1))

    def test_anonymous_deterministic_three_member_round_trip(self):
        xml=junit('<testcase name="private synthetic name" file="/private/path">'
            '<properties><property name="secret" value="private synthetic value"/></properties>'
            '<system-out>private synthetic output</system-out></testcase>')
        raw=self.bundle(xml)
        self.assertEqual(raw,self.bundle(xml))
        self.assertNotIn(b'private',raw)
        receipt,cases=read_bundle(raw,hashlib.sha256(raw).hexdigest())
        self.assertEqual(cases['cases'],[dict(ordinal=1,outcome='passed')])
        self.assertEqual(receipt['dimensions']['provenance'],'BLOCKED')
        self.assertEqual(receipt['dimensions']['freshness'],'NOT_TESTED')

    def test_real_consumer_requires_independent_proof(self):
        raw=self.bundle(); digest=hashlib.sha256(raw).hexdigest()
        e=ExpectedPlatform('source-linux',SOURCE_REPO,'a'*40,'b'*40,'c'*40,
            CONTROLLER_REPO,'c'*40,self.identity.workflow,100,1,200,'Full source',
            ('Sanitize',),300,digest,None,'source-full')
        run=dict(id=100,run_attempt=1,repository=dict(full_name=CONTROLLER_REPO),
            head_sha='c'*40,path=e.workflow,status='completed',conclusion='success',
            html_url=f'https://github.com/{CONTROLLER_REPO}/actions/runs/100')
        job=dict(id=200,run_id=100,run_attempt=1,name=e.job_name,head_sha='c'*40,
            status='completed',conclusion='success',steps=[dict(name='Sanitize',status='completed',conclusion='success')])
        artifact=dict(id=300,expired=False,size_in_bytes=len(raw),digest='sha256:'+digest,
            workflow_run=dict(id=100,head_sha='c'*40))
        source=dict(repo=SOURCE_REPO,head='a'*40,base='b'*40)
        args=dict(raw=raw,run=run,jobs=dict(total_count=1,jobs=[job]),artifact=artifact,
                  source_before=source,source_after=source)
        self.assertEqual(verify_platform(e,**args).state,'ADVISORY_BLOCKED')
        result=verify_platform(e,**args,verify_subject=lambda _: (SOURCE_REPO,'a'*40,None))
        self.assertEqual(result.state,'ADVISORY_VERIFIED')
        self.assertFalse(result.release_authorized)
        self.assertFalse(result.unattended_enabled)

    def test_failure_error_skip_accounting_and_privacy(self):
        for marker,outcome,exit_code in [('failure','failed',1),('error','errors',1),('skipped','skipped',0)]:
            kwargs={dict(failure='failures',error='errors',skipped='skipped')[marker]:1}
            xml=junit(f'<testcase><{marker} message="private synthetic message">private trace</{marker}></testcase>',**kwargs)
            raw=self.bundle(xml,pytest_exit=exit_code)
            receipt,cases=read_bundle(raw,hashlib.sha256(raw).hexdigest())
            self.assertEqual(receipt['counts'][outcome],1)
            self.assertEqual(receipt['dimensions']['test'],'SKIPPED' if marker=='skipped' else 'FAIL')
            self.assertNotIn(b'private',raw)
            self.assertEqual(cases['cases'][0]['outcome'],outcome)

    def test_all_source_platforms_and_exact_identity_validation(self):
        for platform in ('source-linux','windows-py311','windows-py313'):
            self.identity=replace(self.identity,platform=platform)
            receipt,_=read_bundle(self.bundle(),hashlib.sha256(self.bundle()).hexdigest())
            self.assertEqual(receipt['platform'],platform)
        for changes in ({'platform':'docker-standard'},{'run_id':True},{'attempt':0},
                        {'source_sha':'A'*40},{'workflow':'../full.yml'}):
            with self.assertRaises(PlatformRejected):replace(self.identity,**changes)

    def test_exit_and_case_consistency_fail_closed(self):
        for xml,exit_code in [(junit(),1),(junit('<testcase><failure/></testcase>',failures=1),0)]:
            with self.assertRaises(PlatformRejected):self.bundle(xml,pytest_exit=exit_code)
        for code in (True,2,3,4,5,-1):
            with self.assertRaises(PlatformRejected):self.bundle(pytest_exit=code)

    def test_independently_expected_count_cannot_be_overridden_by_xml(self):
        for expected in (True,0,2,10001,None):
            with self.assertRaises(PlatformRejected):self.bundle(expected_cases=expected)
        with self.assertRaises(PlatformRejected):self.bundle(junit('',tests=0))

    def test_counters_must_match_and_be_canonical(self):
        for xml in (junit(tests=2),junit().replace(b'tests="1"',b'tests="01"'),
                    junit().replace(b'failures="0"',b'failures="-0"'),
                    junit().replace(b' errors="0"',b''),
                    junit().replace(b'<testsuites>',b'<testsuites tests="2" failures="0" errors="0" skipped="0">')):
            with self.assertRaises(PlatformRejected):self.bundle(xml)

    def test_nested_or_multiple_outcomes_never_become_passing_cases(self):
        for body in ('<testcase><skipped/><failure/></testcase>',
                     '<testcase><system-out><failure/></system-out></testcase>',
                     '<testcase><unknown/></testcase>',
                     '<properties><testcase/></properties><testcase/>',
                     '<system-out><testcase/></system-out><testcase/>',
                     '<testcase><properties><property><skipped/></property></properties></testcase>'):
            with self.assertRaises(PlatformRejected):self.bundle(junit(body))

    def test_xml_entities_encoding_and_bound_are_rejected_without_raw_messages(self):
        for xml in (b'',b'<private malformed',b'\xff',junit().decode().encode('utf-16'),
                    b'<!DOCTYPE x [<!ENTITY x "private">]>'+junit(), b'x'*(8*1024*1024+1)):
            with self.assertRaises(PlatformRejected) as result:self.bundle(xml)
            self.assertNotIn('private',str(result.exception))

    def test_multiple_suites_and_single_suite_preserve_order(self):
        xml=(b'<testsuites>'+junit()[12:-13]*2+b'</testsuites>')
        counts,rows=anonymous_cases(xml)
        self.assertEqual(counts['passed'],2)
        self.assertEqual([r['ordinal'] for r in rows],[1,2])
        self.assertEqual(anonymous_cases(junit()[12:-13])[0]['passed'],1)

    def test_case_and_suite_limits(self):
        with self.assertRaises(PlatformRejected):anonymous_cases(junit('<testcase/>'*10001,tests=10001))
        suite=junit()[12:-13]
        with self.assertRaises(PlatformRejected):anonymous_cases(b'<testsuites>'+suite*101+b'</testsuites>')
        raw=self.bundle(junit('<testcase/>'*10000,tests=10000),expected_cases=10000)
        self.assertGreater(len(raw),65536)
        self.assertEqual(len(read_bundle(raw,hashlib.sha256(raw).hexdigest())[1]['cases']),10000)


if __name__=='__main__':unittest.main()
