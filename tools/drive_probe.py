"""Upload and verify one synthetic record with existing Drive OAuth credentials."""
import json
import os
import re
import secrets
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DRIVE = "https://www.googleapis.com/drive/v3/files"
SCOPE = "https://www.googleapis.com/auth/drive.file"


def request(url, *, data=None, headers=None):
    with urlopen(Request(url, data=data, headers=headers or {}), timeout=25) as response:
        return response.read()


def probe(credentials, folder_id, send=request):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", folder_id):
        raise ValueError("Invalid destination identifier")
    token = json.loads(send("https://oauth2.googleapis.com/token", data=urlencode({
        **credentials, "grant_type": "refresh_token",
    }).encode()))
    if token.get("scope", SCOPE).split() != [SCOPE] or not token.get("access_token"):
        raise ValueError("Invalid Drive OAuth response")
    auth = {"Authorization": "Bearer " + token["access_token"]}
    folder = json.loads(send(f"{DRIVE}/{folder_id}?" + urlencode({
        "fields": "id,name,mimeType,capabilities(canAddChildren)",
    }), headers=auth))
    if (folder.get("id") != folder_id or folder.get("name") != "Observed Results"
            or folder.get("mimeType") != "application/vnd.google-apps.folder"
            or folder.get("capabilities", {}).get("canAddChildren") is not True):
        raise ValueError("Expected writable Observed Results folder")
    marker = secrets.token_hex(8)
    contents = json.dumps({"kind": "synthetic-ci-connectivity-test", "marker": marker}).encode()
    metadata = json.dumps({"name": f"romarr-ci-drive-probe-{marker}.json",
                           "parents": [folder_id]}).encode()
    boundary = secrets.token_hex(18)
    body = (f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode()
            + metadata + f"\r\n--{boundary}\r\nContent-Type: application/json\r\n\r\n".encode()
            + contents + f"\r\n--{boundary}--\r\n".encode())
    created = json.loads(send(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,parents",
        data=body, headers={**auth, "Content-Type": f"multipart/related; boundary={boundary}"}))
    file_id = created.get("id", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]+", file_id) or created.get("parents") != [folder_id]:
        raise ValueError("Unexpected upload response")
    if send(f"{DRIVE}/{file_id}?alt=media", headers=auth) != contents:
        raise ValueError("Synthetic record readback mismatch")
    return file_id


if __name__ == "__main__":
    try:
        credential = json.loads(os.environ["ROMARR_DRIVE_OAUTH"])
        fields = ("client_id", "client_secret", "refresh_token")
        if not all(type(credential.get(key)) is str and credential[key] for key in fields):
            raise ValueError("Incomplete OAuth credentials")
        probe({key: credential[key] for key in fields}, os.environ["ROMARR_DRIVE_FOLDER"])
    except (HTTPError, URLError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(f"FAIL: Drive probe ({type(exc).__name__})", file=sys.stderr)
        sys.exit(1)
    print("PASS: synthetic Drive upload and byte-for-byte readback")
