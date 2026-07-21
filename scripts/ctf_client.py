#!/usr/bin/env python3
"""CTF Challenge Platform Open API v1 Client.

Usage:
  ctf_client.py image register-reference --name NAME --registry-url URL [--os-type Linux|Windows]
  ctf_client.py image upload-archive --path TAR --name NAME --repository REPO --tag TAG
  ctf_client.py image status --image-id ID
  ctf_client.py image wait-ready --image-id ID [--max-wait SECONDS]
  ctf_client.py image delete --image-id ID

  ctf_client.py challenge import --game-id ID --file JSON_FILE
  ctf_client.py challenge import-batch --game-id ID --file JSON_FILE
  ctf_client.py challenge list --game-id ID [--limit N] [--after CURSOR]
  ctf_client.py challenge get --game-id ID --challenge-id ID
  ctf_client.py challenge delete --game-id ID --challenge-id ID
  ctf_client.py challenge delete-batch --game-id ID --ids ID1,ID2,ID3

  ctf_client.py configure --set KEY=VALUE

Credentials: set GZCTF_HOST + GZCTF_TOKEN env vars, or use --host/--token flags,
or write ~/.gzctf/config.json via the configure command.
"""

import argparse
import email.mime.application
import email.mime.multipart
import email.mime.text
import io
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


# --- Config ---

CONFIG_DIR = Path.home() / ".gzctf"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config():
    """Resolve configuration from env vars or config file."""
    host = os.environ.get("GZCTF_HOST", "")
    token = os.environ.get("GZCTF_TOKEN", "")
    if (not host or not token) and CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            host = host or cfg.get("host", "")
            token = token or cfg.get("token", "")
        except (json.JSONDecodeError, IOError):
            pass
    return host, token


def save_config(**kwargs):
    """Persist key=value pairs to config file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {}
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
        except (json.JSONDecodeError, IOError):
            cfg = {}
    cfg.update(kwargs)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


# --- Error hierarchy ---

class PlatformError(Exception):
    """Base error for all API failures."""
    def __init__(self, message, status=None, detail=None, code=None):
        super().__init__(message)
        self.status = status
        self.detail = detail
        self.code = code


class PlatformAuthError(PlatformError):
    """401 — Token missing, invalid, expired, or revoked."""


class PlatformPermissionError(PlatformError):
    """403 — Missing scope or resource authorization."""


class PlatformNotFoundError(PlatformError):
    """404 — Game, challenge, image, or operation not found."""


class PlatformConflictError(PlatformError):
    """409 — Idempotency-Key conflict (different body with same key)."""


class PlatformValidationError(PlatformError):
    """422 — Business validation failure in request body."""


class PlatformRateLimitError(PlatformError):
    """429 — Token quota exhausted, retry after Retry-After."""


class PlatformUnavailableError(PlatformError):
    """503 — Backend temporarily unavailable."""


class PlatformOperationError(PlatformError):
    """Async operation ended in Failed state."""


# --- HTTP client ---

class PlatformClient:
    """Client for 隐域安全综合演练平台 Open API v1."""

    def __init__(self, host, token, timeout=30):
        if not host:
            raise PlatformError("GZCTF_HOST is not set")
        if not token:
            raise PlatformError("GZCTF_TOKEN is not set")
        # Accept full URL (with protocol+port) or bare hostname
        if host.startswith("http://") or host.startswith("https://"):
            self.base_url = host.rstrip("/")
        else:
            self.base_url = f"http://{host}"
        if not self.base_url.endswith("/api/open/v1"):
            self.base_url += "/api/open/v1"
        self.token = token
        self.timeout = timeout

    # -- Low-level helpers --

    @staticmethod
    def _generate_idempotency_key(prefix):
        """Generate RFC-compliant Idempotency-Key.

        Format: {prefix}-{ISO-date}-{random-8-hex}
        Allowed chars: ASCII letters, digits, -, _, .
        Max length: 128.
        """
        now = datetime.now(timezone.utc).strftime("%Y%m%d")
        rnd = format(random.getrandbits(32), "08x")
        key = f"{prefix}-{now}-{rnd}"
        return key[:128]

    def _request(self, method, path, *, json_body=None, data=None,
                 content_type=None, extra_headers=None, timeout=None):
        """Central request dispatch with error handling."""
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.token}"}
        if extra_headers:
            headers.update(extra_headers)

        body_bytes = None
        if json_body is not None:
            body_bytes = json.dumps(json_body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        elif data is not None:
            body_bytes = data
            if content_type:
                headers["Content-Type"] = content_type

        t = timeout or self.timeout
        req = urllib.request.Request(url, data=body_bytes, headers=headers,
                                     method=method)

        attempt = 0
        max_attempts = 4
        while True:
            attempt += 1
            try:
                with urllib.request.urlopen(req, timeout=t) as resp:
                    raw = resp.read()
                    if not raw:
                        return {}
                    return json.loads(raw)
            except urllib.error.HTTPError as e:
                err_body = {}
                try:
                    err_body = json.loads(e.read())
                except Exception:
                    pass
                detail = err_body.get("detail", "")
                code = err_body.get("code", "")
                status = e.code

                if status == 400:
                    raise PlatformError(detail or "Bad request", status=400,
                                        detail=detail, code=code)
                if status == 401:
                    raise PlatformAuthError(
                        detail or "Token missing, invalid, or expired",
                        status=401, detail=detail, code=code)
                if status == 403:
                    raise PlatformPermissionError(
                        detail or "Insufficient permission", status=403,
                        detail=detail, code=code)
                if status == 404:
                    raise PlatformNotFoundError(detail or "Not found",
                                                status=404, detail=detail,
                                                code=code)
                if status == 409:
                    raise PlatformConflictError(
                        detail or "Idempotency-Key conflict", status=409,
                        detail=detail, code=code)
                if status == 422:
                    raise PlatformValidationError(
                        detail or "Validation failed", status=422,
                        detail=detail, code=code)
                if status == 429:
                    if attempt >= 3:
                        raise PlatformRateLimitError(
                            detail or "Rate limit exceeded", status=429,
                            detail=detail, code=code)
                    retry_after = e.headers.get("Retry-After", "5")
                    try:
                        wait = int(retry_after)
                    except ValueError:
                        wait = 5
                    time.sleep(wait)
                    continue
                if status == 503:
                    if attempt >= max_attempts:
                        raise PlatformUnavailableError(
                            detail or "Service unavailable", status=503,
                            detail=detail, code=code)
                    time.sleep(min(2 ** (attempt - 1), 10))
                    continue
                raise PlatformError(detail or f"HTTP {status}", status=status,
                                    detail=detail, code=code)
            except urllib.error.URLError as e:
                if attempt >= max_attempts:
                    raise PlatformError(f"Network error: {e.reason}")
                time.sleep(min(2 ** (attempt - 1), 10))

    def _poll_operation(self, operation_id, initial_delay=1.0,
                        max_delay=10.0, max_wait=300):
        """Poll GET /operations/{id} until Succeeded or Failed.

        Backoff: 1s, 2s, 4s, 8s, then fixed 10s.
        Raises PlatformOperationError on failure.
        """
        delay = initial_delay
        deadline = time.time() + max_wait
        while True:
            if time.time() > deadline:
                raise PlatformError(
                    f"Operation {operation_id} timed out after {max_wait}s")
            op = self._request("GET", f"/operations/{operation_id}")
            status = op.get("status", -1)
            stage = op.get("stage", "unknown")
            if status == 2:  # Succeeded
                return op
            if status == 3:  # Failed
                raise PlatformOperationError(
                    f"Operation failed at stage '{stage}': "
                    f"{op.get('errorDetail', 'no detail')}",
                    detail=op.get("errorDetail"))
            time.sleep(delay)
            delay = min(delay * 2, max_delay)

    # -- Idempotency helper --

    def _idem_headers(self, key):
        return {
            "Idempotency-Key": key,
        }

    # === Images API ===

    def register_docker_reference(self, name, registry_url, os_type="Linux",
                                  expected_digest=None):
        """POST /images/docker-references — register a registry reference.

        Only 10.24.0.28:5000 or public registries are allowed by the platform.
        Returns: {id, name, registryUrl, osType, status, ...}
        """
        body = {
            "name": name,
            "registryUrl": registry_url,
            "osType": os_type,
        }
        if expected_digest:
            body["expectedDigest"] = expected_digest
        key = self._generate_idempotency_key(f"image-ref-{name}")
        headers = self._idem_headers(key)
        result = self._request("POST", "/images/docker-references",
                               json_body=body, extra_headers=headers)
        op_id = result.get("id")
        if op_id:
            result = self._poll_operation(op_id)
        print(f"Image reference registered: {result.get('result', {}).get('id', 'OK')}")
        return result

    def upload_docker_archive(self, path, name, repository, tag,
                              source_image=None, expected_digest=None):
        """POST /images/docker-archives — upload docker archive tar.

        Uses multipart/form-data to upload the tar file.
        Returns operation, then polls to completion.
        """
        tar_path = Path(path)
        if not tar_path.exists():
            raise PlatformError(f"Archive not found: {path}")
        if not tar_path.is_file():
            raise PlatformError(f"Not a file: {path}")

        # Build multipart form data manually (stdlib only)
        boundary = f"----GzctfUpload{random.getrandbits(64):016x}"
        parts = []

        def add_field(name, value):
            parts.append(f"--{boundary}".encode("utf-8"))
            parts.append(
                f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"))
            parts.append(b"")
            parts.append(str(value).encode("utf-8"))

        def add_file_field(name, filename, data, mime_type):
            parts.append(f"--{boundary}".encode("utf-8"))
            parts.append(
                f'Content-Disposition: form-data; name="{name}"; '
                f'filename="{filename}"'.encode("utf-8"))
            parts.append(f"Content-Type: {mime_type}".encode("utf-8"))
            parts.append(b"")
            parts.append(data)

        add_field("name", name)
        add_field("repository", repository)
        add_field("tag", tag)
        if source_image:
            add_field("sourceImage", source_image)
        if expected_digest:
            add_field("expectedDigest", expected_digest)
        add_file_field("archive", tar_path.name,
                       tar_path.read_bytes(), "application/gzip")
        parts.append(f"--{boundary}--".encode("utf-8"))
        body = b"\r\n".join(p for p in parts)

        content_type = f"multipart/form-data; boundary={boundary}"
        key = self._generate_idempotency_key(f"image-upload-{name}")
        headers = self._idem_headers(key)
        result = self._request("POST", "/images/docker-archives",
                               data=body, content_type=content_type,
                               extra_headers=headers, timeout=600)
        op_id = result.get("id")
        if op_id:
            result = self._poll_operation(op_id, max_wait=600)
        print(f"Image archive uploaded: {result.get('result', {}).get('id', 'OK')}")
        return result

    def get_image_status(self, image_template_id):
        """GET /images/{imageTemplateId} — query image template."""
        return self._request("GET", f"/images/{image_template_id}")

    # Image status enum (doc: 0=Ready, 1=Importing, 2=Error, 3=Deleting)
    IMAGE_STATUS_READY = 0
    IMAGE_STATUS_IMPORTING = 1
    IMAGE_STATUS_ERROR = 2
    IMAGE_STATUS_DELETING = 3

    def wait_for_image_ready(self, image_template_id, max_wait=300):
        """Poll GET /images/{imageTemplateId} until status is Ready (0)."""
        delay = 2.0
        deadline = time.time() + max_wait
        while True:
            if time.time() > deadline:
                raise PlatformError(
                    f"Image {image_template_id} not Ready after {max_wait}s")
            info = self.get_image_status(image_template_id)
            status = info.get("status", -1)
            if status == self.IMAGE_STATUS_READY:
                return info
            if status == self.IMAGE_STATUS_ERROR:
                raise PlatformError(
                    f"Image {image_template_id} import failed: "
                    f"{info.get('errorMessage', 'no detail')}")
            time.sleep(delay)
            delay = min(delay * 1.5, 10)

    def delete_image(self, image_template_id):
        """DELETE /images/{imageTemplateId} — delete unused image template."""
        key = self._generate_idempotency_key(f"image-delete-{image_template_id}")
        headers = self._idem_headers(key)
        result = self._request("DELETE", f"/images/{image_template_id}",
                               extra_headers=headers)
        op_id = result.get("id")
        if op_id:
            result = self._poll_operation(op_id)
        print(f"Image {image_template_id} deleted")
        return result

    # === Challenges API ===

    def import_challenge(self, game_id, challenge_def):
        """POST /games/{gameId}/challenges — import a single challenge.

        challenge_def is a dict with all required fields per challenge type.
        Returns operation -> polls to completion -> result contains challengeId.
        """
        external_id = challenge_def.get("externalId", "unknown")
        key = self._generate_idempotency_key(
            f"challenge-import-{game_id}-{external_id}")
        headers = self._idem_headers(key)
        result = self._request("POST", f"/games/{game_id}/challenges",
                               json_body=challenge_def, extra_headers=headers)
        op_id = result.get("id")
        if op_id:
            result = self._poll_operation(op_id)
        op_result = result.get("result", {})
        challenge_id = op_result.get("challengeId") if isinstance(op_result, dict) else None
        print(f"Challenge imported: externalId={external_id}, challengeId={challenge_id}")
        return result

    def import_challenges_batch(self, game_id, items):
        """POST /games/{gameId}/challenges/batch — atomic batch import (1-100).

        items is a list of challenge dicts. Each must have unique externalId.
        Returns operation -> polls -> result.imported = [{externalId, challengeId}].
        """
        batch_id = items[0].get("externalId", "batch") if items else "batch"
        key = self._generate_idempotency_key(
            f"challenge-batch-{game_id}-{batch_id}")
        headers = self._idem_headers(key)
        body = {"items": items}
        result = self._request("POST", f"/games/{game_id}/challenges/batch",
                               json_body=body, extra_headers=headers)
        op_id = result.get("id")
        if op_id:
            result = self._poll_operation(op_id)
        op_result = result.get("result", {})
        imported = op_result.get("imported", []) if isinstance(op_result, dict) else []
        for entry in imported:
            print(f"  {entry['externalId']} -> challengeId={entry['challengeId']}")
        return result

    def list_challenges(self, game_id, limit=50, after=None):
        """GET /games/{gameId}/challenges — cursor-paginated query."""
        params = [f"limit={limit}"]
        if after:
            params.append(f"after={after}")
        qs = "&".join(params)
        return self._request("GET", f"/games/{game_id}/challenges?{qs}")

    def get_challenge(self, game_id, challenge_id):
        """GET /games/{gameId}/challenges/{challengeId} — full detail incl. flags."""
        return self._request("GET",
                             f"/games/{game_id}/challenges/{challenge_id}")

    def delete_challenge(self, game_id, challenge_id):
        """DELETE /games/{gameId}/challenges/{challengeId} — stop env + delete."""
        key = self._generate_idempotency_key(
            f"challenge-delete-{game_id}-{challenge_id}")
        headers = self._idem_headers(key)
        result = self._request("DELETE",
                               f"/games/{game_id}/challenges/{challenge_id}",
                               extra_headers=headers)
        op_id = result.get("id")
        if op_id:
            result = self._poll_operation(op_id)
        print(f"Challenge {challenge_id} deleted")
        return result

    def delete_challenges_batch(self, game_id, challenge_ids):
        """POST /games/{gameId}/challenges/batch-delete — batch delete 1-100."""
        key = self._generate_idempotency_key(
            f"challenge-batch-delete-{game_id}")
        headers = self._idem_headers(key)
        body = {"challengeIds": challenge_ids}
        result = self._request("POST",
                               f"/games/{game_id}/challenges/batch-delete",
                               json_body=body, extra_headers=headers)
        op_id = result.get("id")
        if op_id:
            result = self._poll_operation(op_id)
        op_result = result.get("result", {})
        deleted = op_result.get("deleted", []) if isinstance(op_result, dict) else []
        missing = op_result.get("missing", []) if isinstance(op_result, dict) else []
        print(f"Deleted: {len(deleted)}, already missing: {len(missing)}")
        return result


# --- CLI ---

def _make_parser():
    parser = argparse.ArgumentParser(
        description="隐域安全综合演练平台 Open API v1 Client")
    parser.add_argument("--host", default="",
                        help="Platform host (or set GZCTF_HOST)")
    parser.add_argument("--token", default="",
                        help="API token (or set GZCTF_TOKEN)")
    parser.add_argument("--config", default=str(CONFIG_FILE),
                        help="Config file path")
    parser.add_argument("--json", dest="raw_json", action="store_true",
                        help="Output raw JSON")
    parser.add_argument("--verbose", action="store_true",
                        help="Verbose logging")

    sub = parser.add_subparsers(dest="command")
    sub.required = True

    # --- image ---
    img = sub.add_parser("image", help="Image management")
    img_sub = img.add_subparsers(dest="subcommand")
    img_sub.required = True

    irr = img_sub.add_parser("register-reference",
                             help="Register a Docker reference")
    irr.add_argument("--name", required=True)
    irr.add_argument("--registry-url", required=True)
    irr.add_argument("--os-type", default="Linux", choices=["Linux", "Windows"])
    irr.add_argument("--expected-digest", default=None,
                     help="SHA-256 digest of the image (hex)")

    iua = img_sub.add_parser("upload-archive", help="Upload a Docker archive tar")
    iua.add_argument("--path", required=True, help="Path to .tar file")
    iua.add_argument("--name", required=True)
    iua.add_argument("--repository", required=True)
    iua.add_argument("--tag", required=True)
    iua.add_argument("--source-image", default=None)
    iua.add_argument("--expected-digest", default=None,
                     help="SHA-256 digest of the archive file (hex)")

    ist = img_sub.add_parser("status", help="Check image template status")
    ist.add_argument("--image-id", required=True, type=int)

    iwr = img_sub.add_parser("wait-ready", help="Poll until image is Ready")
    iwr.add_argument("--image-id", required=True, type=int)
    iwr.add_argument("--max-wait", type=int, default=300)

    idl = img_sub.add_parser("delete", help="Delete unused image template")
    idl.add_argument("--image-id", required=True, type=int)

    # --- challenge ---
    ch = sub.add_parser("challenge", help="Challenge management")
    ch_sub = ch.add_subparsers(dest="subcommand")
    ch_sub.required = True

    cim = ch_sub.add_parser("import", help="Import a single challenge")
    cim.add_argument("--game-id", required=True, type=int)
    cim.add_argument("--file", required=True, help="JSON file with challenge definition")

    cib = ch_sub.add_parser("import-batch", help="Batch import challenges")
    cib.add_argument("--game-id", required=True, type=int)
    cib.add_argument("--file", required=True,
                     help="JSON file with array of challenge definitions")

    cli = ch_sub.add_parser("list", help="List challenges in a game")
    cli.add_argument("--game-id", required=True, type=int)
    cli.add_argument("--limit", type=int, default=50)
    cli.add_argument("--after", default=None)

    cge = ch_sub.add_parser("get", help="Get challenge details")
    cge.add_argument("--game-id", required=True, type=int)
    cge.add_argument("--challenge-id", required=True, type=int)

    cde = ch_sub.add_parser("delete", help="Delete a challenge")
    cde.add_argument("--game-id", required=True, type=int)
    cde.add_argument("--challenge-id", required=True, type=int)

    cdb = ch_sub.add_parser("delete-batch", help="Batch delete challenges")
    cdb.add_argument("--game-id", required=True, type=int)
    cdb.add_argument("--ids", required=True,
                     help="Comma-separated challenge IDs")

    # --- configure ---
    cfg = sub.add_parser("configure", help="Manage client configuration")
    cfg.add_argument("--set", dest="set_pair", required=True,
                     help="KEY=VALUE to persist (e.g. host=platform.example.com)")

    return parser


def main():
    parser = _make_parser()
    args = parser.parse_args()

    # Resolve config
    cfg_host, cfg_token = load_config()
    host = args.host or cfg_host
    token = args.token or cfg_token

    # configure command doesn't need a client
    if args.command == "configure":
        if "=" not in args.set_pair:
            print("ERROR: --set must be KEY=VALUE", file=sys.stderr)
            sys.exit(1)
        key, _, value = args.set_pair.partition("=")
        save_config(**{key: value})
        print(f"Saved {key}={value}")
        return

    client = PlatformClient(host, token)

    def print_result(result):
        if args.raw_json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif isinstance(result, dict):
            print(json.dumps(result, indent=2, ensure_ascii=False))

    try:
        # --- image commands ---
        if args.command == "image":
            if args.subcommand == "register-reference":
                r = client.register_docker_reference(
                    args.name, args.registry_url, args.os_type,
                    args.expected_digest)
                print_result(r)
            elif args.subcommand == "upload-archive":
                r = client.upload_docker_archive(
                    args.path, args.name, args.repository, args.tag,
                    args.source_image, args.expected_digest)
                print_result(r)
            elif args.subcommand == "status":
                r = client.get_image_status(args.image_id)
                print_result(r)
            elif args.subcommand == "wait-ready":
                r = client.wait_for_image_ready(args.image_id, args.max_wait)
                print_result(r)
            elif args.subcommand == "delete":
                r = client.delete_image(args.image_id)
                print_result(r)

        # --- challenge commands ---
        elif args.command == "challenge":
            if args.subcommand == "import":
                with open(args.file) as f:
                    ch_def = json.load(f)
                r = client.import_challenge(args.game_id, ch_def)
                print_result(r)
            elif args.subcommand == "import-batch":
                with open(args.file) as f:
                    items = json.load(f)
                if not isinstance(items, list):
                    print("ERROR: batch file must contain a JSON array",
                          file=sys.stderr)
                    sys.exit(1)
                r = client.import_challenges_batch(args.game_id, items)
                print_result(r)
            elif args.subcommand == "list":
                r = client.list_challenges(args.game_id, args.limit, args.after)
                print_result(r)
            elif args.subcommand == "get":
                r = client.get_challenge(args.game_id, args.challenge_id)
                print_result(r)
            elif args.subcommand == "delete":
                r = client.delete_challenge(args.game_id, args.challenge_id)
                print_result(r)
            elif args.subcommand == "delete-batch":
                ids = [int(x.strip()) for x in args.ids.split(",")]
                r = client.delete_challenges_batch(args.game_id, ids)
                print_result(r)

    except (PlatformAuthError, PlatformPermissionError,
            PlatformNotFoundError, PlatformConflictError,
            PlatformValidationError, PlatformRateLimitError,
            PlatformUnavailableError, PlatformOperationError,
            PlatformError) as e:
        print(f"ERROR [{e.status}]: {e}", file=sys.stderr)
        if e.detail:
            print(f"  Detail: {e.detail}", file=sys.stderr)
        if e.code:
            print(f"  Code: {e.code}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
