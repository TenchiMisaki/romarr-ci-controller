"""Proposed canary criterion on disposable real Git, never hosted acceptance."""
import copy
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from durable_state import PREFIX, StateBlocked
from hosted_state_canary import (CanaryAPI, CanaryConflict, CanaryHTTPFailure,
    Wire, exercise, verify_race_candidates)
from test_hosted_state_canary import FixtureWire, REF


class SiblingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.wire = FixtureWire(self.temp.name)
        self.api = CanaryAPI(self.wire, REF)
        self.seed = self.api.seed(self.wire.git.head())

    def generic_wire(self, method, path, body=None):
        try:
            return self.wire(method, path, body)
        except CanaryConflict:
            raise CanaryHTTPFailure(422, 'PATCH', 'REFERENCE_CANNOT_BE_UPDATED') from None

    def test_generic_rejections_require_verified_siblings_and_remain_separate(self):
        self.api.wire = self.generic_wire
        result = exercise(self.api)
        self.assertEqual(result['race_evidence'], dict(candidates=8,
            distinct_siblings=True, canonical_disabled_tree=True,
            explicit_non_fast_forward=0, generic_reference_rejected=7))
        self.assertEqual(result['operational_acceptance'], 'NOT TESTED')
        self.assertFalse(result['source_dispatch_allowed'])
        self.assertEqual(self.wire.git.patches, 9)
        self.wire.git.run('fsck', '--strict', '--no-reflogs')

    def test_tampered_candidate_readbacks_block_before_recovery_write(self):
        for defect in ('sha', 'tree', 'parent', 'merge', 'missing', 'malformed'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as root:
                wire = FixtureWire(root)
                api = CanaryAPI(wire, REF)
                api.seed(wire.git.head())
                def tamper(method, path, body=None):
                    try:
                        row = wire(method, path, body)
                    except CanaryConflict:
                        raise CanaryHTTPFailure(422, 'PATCH', 'REFERENCE_CANNOT_BE_UPDATED') from None
                    if method == 'GET' and '/git/commits/' in '/'+path and len(api.created) == 8 and api.barrier is None:
                        row = copy.deepcopy(row)
                        if defect == 'sha': row['sha'] = 'a'*40
                        if defect == 'tree': row['tree']['sha'] = 'a'*40
                        if defect == 'parent': row['parents'] = [dict(sha='a'*40)]
                        if defect == 'merge': row['parents'].append(dict(sha='a'*40))
                        if defect == 'missing': row.pop('parents')
                        if defect == 'malformed': row['tree'] = []
                    return row
                api.wire = tamper
                with self.assertRaisesRegex(StateBlocked, 'CANARY_CANDIDATE_EVIDENCE_INVALID'):
                    exercise(api)
                self.assertFalse(api.drop_response)
                self.assertEqual(wire.git.patches, 8)

    def test_missing_duplicate_foreign_and_multiple_winner_outcomes_refused_without_reads(self):
        targets = [format(n, '040x') for n in range(1, 9)]
        good = [('winner' if i == 0 else 'generic_rejected', sha) for i, sha in enumerate(targets)]
        self.api.created = set(targets)
        invalid = [good[:-1], good[:-1]+[good[0]], [('winner', None)]+good[1:],
                   [('winner', 'f'*40)]+good[1:],
                   good[:1]+[('winner', targets[1])]+good[2:],
                   good[:1]+[('error', targets[1])]+good[2:]]
        before = len(self.wire.calls)
        for outcomes in invalid:
            with self.subTest(outcomes=outcomes), self.assertRaises(StateBlocked):
                verify_race_candidates(self.api, self.seed, outcomes)
        self.assertEqual(len(self.wire.calls), before)

    def test_unexpected_http_rejection_still_blocks_before_candidate_acceptance(self):
        original = self.wire
        def deny(method, path, body=None):
            if method == 'PATCH':
                raise CanaryHTTPFailure(403, 'PATCH', 'OTHER_RESPONSE')
            return original(method, path, body)
        self.api.wire = deny
        progress = {}
        with self.assertRaisesRegex(StateBlocked, 'CANARY_RACE_WRITER_FAILED'):
            exercise(self.api, progress)
        self.assertNotIn('race_evidence', progress)
        self.assertFalse(self.api.drop_response)

    def test_changed_ref_after_commit_reads_blocks_recovery(self):
        self.api.wire = self.generic_wire
        original = self.api.request
        def changed(method, path, body=None):
            row = original(method, path, body)
            if (method == 'GET' and path == PREFIX+'git/ref/heads/controller-state-v1'
                    and self.api.barrier is None and len(self.api.created) == 8):
                row['object']['sha'] = self.seed
            return row
        self.api.request = changed
        with self.assertRaisesRegex(StateBlocked, 'CANARY_WINNER_READBACK_INVALID'):
            exercise(self.api)
        self.assertFalse(self.api.drop_response)
        self.assertEqual(self.wire.git.patches, 8)

    def test_real_http_short_sized_read_cannot_qualify_generic_rejection(self):
        from http.client import HTTPResponse
        raw = json.dumps(dict(message='Reference cannot be updated')).encode()
        class Socket:
            def makefile(self, mode):
                return io.BytesIO(b'HTTP/1.1 422 Invalid\r\nContent-Length: '+
                    str(len(raw)+1).encode()+b'\r\n\r\n'+raw)
        response = HTTPResponse(Socket())
        response.begin()
        class Opener:
            def open(self, req, timeout):
                raise HTTPError(req.full_url, 422, 'private', response.headers, response)
        with patch('hosted_state_canary.build_opener', return_value=Opener()):
            with self.assertRaises(CanaryHTTPFailure) as caught:
                Wire('synthetic-fixture')('PATCH', PREFIX+'git/refs/'+REF)
        self.assertEqual(caught.exception.reason, 'OTHER_RESPONSE')
        self.assertEqual(caught.exception.response['body_read'], 'INCOMPLETE')
        self.assertEqual(caught.exception.response['captured_bytes'], len(raw))
        self.assertTrue(response.closed)

    def test_declared_length_must_be_valid_and_match_captured_bytes(self):
        raw = json.dumps(dict(message='Reference cannot be updated')).encode()
        for declared in (str(len(raw)), str(len(raw)-1), '-1', 'invalid', '9'*5000):
            class Opener:
                def open(self, req, timeout):
                    raise HTTPError(req.full_url, 422, 'private',
                        {'Content-Length': declared}, io.BytesIO(raw))
            with self.subTest(declared=declared[:20]):
                with patch('hosted_state_canary.build_opener', return_value=Opener()):
                    with self.assertRaises(CanaryHTTPFailure) as caught:
                        Wire('synthetic-fixture')('PATCH', PREFIX+'git/refs/'+REF)
                complete = declared == str(len(raw))
                self.assertEqual(caught.exception.reason == 'REFERENCE_CANNOT_BE_UPDATED', complete)
                self.assertEqual(caught.exception.response['body_read'], 'SUCCESS' if complete else 'INCOMPLETE')

    def test_generic_message_is_separate_and_only_complete_identity_patch_422(self):
        for status, method, encoding, message in [
                (422, 'PATCH', 'identity', 'Reference cannot be updated'),
                (409, 'PATCH', 'identity', 'Reference cannot be updated'),
                (403, 'PATCH', 'identity', 'Reference cannot be updated'),
                (422, 'POST', 'identity', 'Reference cannot be updated'),
                (422, 'PATCH', 'gzip', 'Reference cannot be updated'),
                (422, 'PATCH', 'identity', 'Reference cannot be updated.')]:
            class Opener:
                def open(self, req, timeout):
                    raise HTTPError(req.full_url, status, 'private',
                        {'Content-Encoding': encoding},
                        io.BytesIO(json.dumps(dict(message=message)).encode()))
            with self.subTest(status=status, method=method, encoding=encoding, message=message):
                with patch('hosted_state_canary.build_opener', return_value=Opener()):
                    with self.assertRaises(CanaryHTTPFailure) as caught:
                        Wire('synthetic-fixture')(method, PREFIX+'git/refs/'+REF)
                expected = (status, method, encoding, message) == (422, 'PATCH', 'identity', 'Reference cannot be updated')
                self.assertEqual(caught.exception.reason == 'REFERENCE_CANNOT_BE_UPDATED', expected)
                self.assertNotIsInstance(caught.exception, CanaryConflict)
