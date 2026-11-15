"""Offline positive and adversarial cases for both ROMarr evidence formats."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "controller"))
from public_evidence import EvidenceError, inspect  # noqa: E402

H = "a" * 40
B = "b" * 40


def archive(official=True, *, mutate=None):
    repository = "BlizzHacker/romarr" if official else "TenchiMisaki/romarr"
    cases = [{"id": 1 if official else "case-000001", "outcome": "passed"},
             {"id": 2 if official else "case-000002", "outcome": "skipped"}]
    if official:
        summary = dict(schema=1, repository=repository, tested_head=H, tested_base=B,
                       scope="full", test="PASS", environment="PASS", collection="PASS",
                       source="UNCHANGED", exit=0,
                       counts=dict(passed=1, failed=0, error=0, skipped=1))
        docs = {"summary.json": summary, "cases.json": cases}
    else:
        counts = dict(passed=1, failed=0, errors=0, skipped=1)
        summary = dict(schema="romarr-ci-result-v1", repository=repository,
                       tested_sha=H, base_sha=B, scope="full", test_status="PASS",
                       environment_status="PASS", collection_status="PASS",
                       pytest_exit_code=0, counts=counts, run_id="42", run_attempt="1")
        docs = {"summary.json": summary, "postcheck.json": dict(status="UNCHANGED", tested_sha=H),
                "testcases.json": dict(schema="pr-pytest-cases-v1", repository=repository,
                                       tested_sha=H, scope="full", counts=counts,
                                       run_id="42", run_attempt="1", cases=cases),
                "HANDOFF.md": "sanitized handoff only\n"}
    if mutate:
        mutate(docs)
    data = {name:(value.encode() if isinstance(value,str) else json.dumps(value,sort_keys=True).encode())
            for name,value in docs.items()}
    hashes = {name:hashlib.sha256(value).hexdigest() for name,value in data.items()}
    manifest = hashes if official else {"schema":"romarr-ci-manifest-v1","files":hashes}
    data["manifest.json"] = json.dumps(manifest,sort_keys=True).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED) as z:
        for name,value in data.items():
            z.writestr(name,value)
    return stream.getvalue()


class EvidenceContract(unittest.TestCase):
    def verify(self, payload, official=True, **kwargs):
        repository="BlizzHacker/romarr" if official else "TenchiMisaki/romarr"
        expected=dict(repository=repository,head=H,base=B,scope="full")
        expected.update(kwargs)
        return inspect(io.BytesIO(payload), **expected)

    def test_upstream_positive(self):
        result=self.verify(archive())
        self.assertEqual(result["counts"],{"passed":1,"failed":0,"error":0,"skipped":1})
        self.assertEqual(result["github_run_identity"],"EXTERNAL_VERIFICATION_REQUIRED")
        self.assertTrue(result["skips_require_review"])

    def test_controller_positive(self):
        result=self.verify(archive(False),False)
        self.assertEqual(result["counts"],{"passed":1,"failed":0,"errors":0,"skipped":1})

    def test_changed_head_or_base_is_rejected(self):
        for official in (True,False):
            for key in ("head","base"):
                with self.subTest(official=official,key=key),self.assertRaises(EvidenceError):
                    self.verify(archive(official),official, **{key:"c"*40})

    def test_changed_source_counts_or_scope_is_rejected(self):
        for official in (True,False):
            for field,value in (("scope","structural"),("counts",{"passed":99})): 
                with self.subTest(official=official,field=field),self.assertRaises(EvidenceError):
                    self.verify(archive(official,mutate=lambda docs: docs["summary.json"].__setitem__(field,value)),official)

    def test_test_failures_and_missing_gates_are_rejected(self):
        for official in (True,False):
            fields=[("test","FAIL"),( "environment","FAIL"),("source","STALE_OR_UNVERIFIED")] if official else [
                ("test_status","FAIL"),("collection_status","FAILED"),("pytest_exit_code",1)]
            for field,value in fields:
                with self.subTest(official=official,field=field),self.assertRaises(EvidenceError):
                    self.verify(archive(official,mutate=lambda docs:docs["summary.json"].__setitem__(field,value)),official)

    def test_tampered_checksum_is_rejected(self):
        for official in (True,False):
            payload=archive(official)
            source=io.BytesIO(payload)
            destination=io.BytesIO()
            with zipfile.ZipFile(source) as z, zipfile.ZipFile(destination,"w",zipfile.ZIP_DEFLATED) as dst:
                for name in z.namelist():
                    value=z.read(name)
                    if name=="summary.json":value+=b" "
                    dst.writestr(name,value)
            with self.subTest(official=official),self.assertRaises(EvidenceError):
                self.verify(destination.getvalue(),official)

    def test_missing_extra_and_nested_files_are_rejected(self):
        for new_name in ("private.xml","../evil.txt","subdir/summary.json"):
            payload=archive()
            out=io.BytesIO()
            with zipfile.ZipFile(io.BytesIO(payload)) as src,zipfile.ZipFile(out,"w") as dst:
                for name in src.namelist():dst.writestr(name,src.read(name))
                dst.writestr(new_name,b"private")
            with self.subTest(name=new_name),self.assertRaises(EvidenceError):
                self.verify(out.getvalue())

    def test_non_anonymous_or_out_of_order_cases_are_rejected(self):
        for official in (True,False):
            def change(docs):
                key="cases.json" if official else "testcases.json"
                cases=docs[key] if official else docs[key]["cases"]
                cases[0]["name"]="private-secret"
            with self.subTest(official=official),self.assertRaises(EvidenceError):
                self.verify(archive(official,mutate=change),official)

    def test_controller_case_identity_mismatch_is_rejected(self):
        with self.assertRaises(EvidenceError):
            self.verify(archive(False,mutate=lambda docs:docs["testcases.json"].__setitem__("run_id","43")),False)

    def test_boolean_case_count_is_not_a_valid_integer(self):
        for official in (True, False):
            with self.subTest(official=official), self.assertRaises(EvidenceError):
                self.verify(archive(official, mutate=lambda docs: docs["summary.json"]["counts"].__setitem__("passed", True)), official)

    def test_boolean_exit_is_not_a_valid_zero_exit(self):
        for official in (True, False):
            field = "exit" if official else "pytest_exit_code"
            with self.subTest(official=official), self.assertRaises(EvidenceError):
                self.verify(archive(official, mutate=lambda docs: docs["summary.json"].__setitem__(field, False)), official)

    def test_invalid_zip_is_rejected(self):
        with self.assertRaises(EvidenceError):
            self.verify(b"not a zip archive")

    def test_duplicate_json_keys_are_rejected(self):
        payload = archive()
        target = io.BytesIO()
        with zipfile.ZipFile(io.BytesIO(payload)) as original, zipfile.ZipFile(target, "w") as updated:
            for name in original.namelist():
                value = original.read(name)
                if name == "summary.json":
                    value = value[:-1] + b', "scope": "full"}'
                updated.writestr(name, value)
        with self.assertRaises(EvidenceError):
            self.verify(target.getvalue())

    def test_unrecognized_repository_rejected(self):
        with self.assertRaises(EvidenceError):
            self.verify(archive(),repository="untrusted/repo")


if __name__ == "__main__":
    unittest.main()
