from __future__ import annotations

import base64
import fnmatch
import imaplib
import logging
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from email import message_from_bytes
from ftplib import FTP, FTP_TLS
from pathlib import Path
from stat import S_ISREG
from typing import Any

logger = logging.getLogger(__name__)

_ZIP_MAGIC = b"PK\x03\x04"


def _certifi_cafile() -> str | None:
    try:
        import certifi

        return certifi.where()
    except ImportError:
        return None


def _https_ssl_contexts() -> list[ssl.SSLContext]:
    """Ordered SSL profiles: Mozilla CA bundle (certifi) often fixes Windows chain errors; then system default; then legacy TLS."""
    cafile = _certifi_cafile()
    out: list[ssl.SSLContext] = []

    def add(ctx: ssl.SSLContext) -> None:
        out.append(ctx)

    if cafile:
        try:
            add(ssl.create_default_context(cafile=cafile))
        except Exception:
            pass
    add(ssl.create_default_context())

    def _legacy(seclevel1: bool) -> ssl.SSLContext | None:
        try:
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            if cafile:
                try:
                    ctx.load_verify_locations(cafile=cafile)
                except ssl.SSLError:
                    pass
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
            if hasattr(ssl, "OP_LEGACY_SERVER_CONNECT"):
                ctx.options |= ssl.OP_LEGACY_SERVER_CONNECT
            if seclevel1:
                ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
            return ctx
        except ssl.SSLError:
            return None
        except Exception:
            return None

    for sec1 in (False, True):
        c = _legacy(sec1)
        if c is not None:
            add(c)

    unverified: list[ssl.SSLContext] = []
    if os.environ.get("FEED_HTTP_SSL_NO_VERIFY", "").strip().lower() in ("1", "true", "yes"):
        unverified.append(ssl._create_unverified_context())
        logger.warning(
            "FEED_HTTP_SSL_NO_VERIFY enabled: HTTPS feeds will not verify certificates (mitm risk).",
        )

    if os.environ.get("FEED_HTTP_SSL_LEGACY", "").strip().lower() in ("1", "true", "yes"):
        out.reverse()
    return out + unverified


def zip_pick_inner_bytes(zip_bytes: bytes, pattern: str) -> bytes:
    """Pick one member from a ZIP; ``pattern`` is a glob (e.g. ``*.csv``) or an exact entry path."""
    from io import BytesIO

    pat = (pattern or "*.csv").strip() or "*.csv"
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        names = [n for n in zf.namelist() if not n.endswith("/")]
        if not names:
            raise ValueError("ZIP archive has no files")
        chosen: str | None = None
        if pat in names:
            chosen = pat
        else:
            for n in names:
                norm = n.replace("\\", "/")
                base = norm.rsplit("/", 1)[-1]
                if fnmatch.fnmatch(base, pat) or fnmatch.fnmatch(norm, pat):
                    chosen = n
                    break
        if chosen is None:
            csvs = [n for n in names if n.lower().endswith(".csv")]
            if csvs:
                chosen = sorted(csvs, key=lambda x: (x.count("/"), len(x)))[0]
        if chosen is None:
            raise ValueError(
                f"No ZIP entry matched {pat!r}; try a more specific “zip inner pattern”. "
                f"Members (first 15): {names[:15]}",
            )
        return zf.read(chosen)


def _detect_excel_header_row(raw, *, max_scan: int = 45) -> int:
    """Row index in a header=None frame that most likely contains column titles (skip cover/title rows)."""
    import pandas as pd

    if raw.empty:
        return 0
    header_kw = re.compile(
        r"part|sku|mpn|oem|model|price|cost|trade|buy|sell|stock|qty|quantity|on.?hand|"
        r"brand|mfr|manuf|vendor|desc|description|product|item|ean|upc|code|unit|rrp|gbp|eur|usd|avail",
        re.I,
    )
    numeric_row = re.compile(r"^[\d.,\s€$£¥%-]+$")
    best_i = 0
    best_score = -1.0
    nrows = min(max_scan, len(raw))
    for i in range(nrows):
        cells: list[str] = []
        for v in raw.iloc[i]:
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            s = str(v).strip()
            if not s or s.lower() == "nan":
                continue
            cells.append(s)
        if len(cells) < 2:
            continue
        num_like = sum(1 for s in cells if numeric_row.match(s))
        if num_like >= max(len(cells) - 1, 1) * 0.65:
            continue
        keyword_hits = sum(2 if header_kw.search(s) else 0 for s in cells)
        score = float(keyword_hits) + len(cells) * 0.2
        if score > best_score:
            best_score = score
            best_i = i
    if best_score >= 2.0:
        return best_i
    for i in range(nrows):
        cells = []
        for v in raw.iloc[i]:
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            s = str(v).strip()
            if not s or s.lower() == "nan":
                continue
            cells.append(s)
        if len(cells) >= 3:
            num_like = sum(1 for s in cells if numeric_row.match(s))
            if num_like < len(cells) * 0.5:
                return i
    return 0


def _unique_dataframe_columns(names: list[str]) -> list[str]:
    counts: dict[str, int] = {}
    out: list[str] = []
    for c in names:
        base = (c or "").strip() or "column"
        n = counts.get(base, 0)
        counts[base] = n + 1
        out.append(base if n == 0 else f"{base}_{n + 1}")
    return out


def _zip_is_xlsx(data: bytes) -> bool:
    """True if bytes are a ZIP container for an Office Open XML spreadsheet (.xlsx), not a CSV-in-ZIP."""
    from io import BytesIO

    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            names = set(zf.namelist())
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in names and "xl/workbook.xml" in names


def _xlsx_bytes_to_csv_file(path: Path, data: bytes) -> None:
    """Rewrite ``path`` as UTF-8 CSV from the first sheet of an .xlsx (for ``VendorACsvAdapter`` / ``main.py``)."""
    from io import BytesIO

    import pandas as pd

    bio = BytesIO(data)
    try:
        raw = pd.read_excel(bio, engine="openpyxl", dtype=str, header=None)
    except Exception as exc:
        raise ValueError(f"Could not read Excel from downloaded file: {exc}") from exc
    h = _detect_excel_header_row(raw)
    df = raw.iloc[h + 1 :].copy()
    raw_cols: list[str] = []
    for j in range(raw.shape[1]):
        v = raw.iloc[h, j]
        if v is None or (isinstance(v, float) and pd.isna(v)):
            s = ""
        else:
            s = str(v).strip()
        if not s or s.lower() == "nan":
            s = f"Column_{j}"
        raw_cols.append(s)
    df.columns = _unique_dataframe_columns(raw_cols)
    df = df.dropna(how="all")
    df.reset_index(drop=True, inplace=True)
    out_path = path if path.suffix.lower() == ".csv" else path.with_suffix(".csv")
    df.to_csv(out_path, index=False, encoding="utf-8")
    if out_path.resolve() != path.resolve():
        path.unlink(missing_ok=True)
    logger.info(
        "Converted XLSX -> %s (%s rows, %s cols, header_row=%s, columns=%s)",
        out_path,
        len(df),
        len(df.columns),
        h,
        list(df.columns)[:12],
    )


def finalize_local_feed_file(path: Path, src: dict[str, Any]) -> None:
    """Normalize downloaded file: XLSX → CSV; else if ZIP of CSV, extract inner CSV via ``zip_inner_pattern``."""
    data = path.read_bytes()
    if len(data) < 4 or data[:4] != _ZIP_MAGIC:
        return
    if _zip_is_xlsx(data):
        _xlsx_bytes_to_csv_file(path, data)
        return
    inner_pat = str(src.get("zip_inner_pattern") or "*.csv")
    out = zip_pick_inner_bytes(data, inner_pat)
    path.write_bytes(out)
    logger.info("Unpacked ZIP -> %s (%s bytes)", path, len(out))


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _resolve_local_path(project_root: Path, local_path: str | Path) -> Path:
    p = Path(local_path)
    if not p.is_absolute():
        p = project_root / p
    return p


def _normalize_host_port(host_raw: str, config_port: int) -> tuple[str, int]:
    """
    Turn ``host`` into a DNS name or IP for ``socket``/FTP/SFTP.

    Strips accidental ``ftp://`` / ``sftp://`` prefixes (and optional ``user@``, path)
    so callers that pasted a full URI do not trigger getaddrinfo failures.
    """
    s = str(host_raw).strip()
    if not s:
        raise ValueError("Host is empty")
    if "://" in s:
        parsed = urllib.parse.urlparse(s)
        hostname = (parsed.hostname or "").strip()
        if not hostname:
            raise ValueError(f"Could not parse hostname from {host_raw!r}")
        port = parsed.port if parsed.port is not None else config_port
        return hostname, port
    if ":" in s and not s.startswith("["):
        host_part, port_part = s.rsplit(":", 1)
        if port_part.isdigit():
            return host_part.strip(), int(port_part)
    return s, config_port


def fetch_sftp(src: dict[str, Any], project_root: Path, password: str | None) -> Path:
    import paramiko

    config_port = int(src.get("port", 22))
    host, port = _normalize_host_port(str(src["host"]), config_port)
    username = str(src["username"])
    local_path = _resolve_local_path(project_root, str(src["local_path"]))
    _ensure_parent(local_path)

    key_inline = str(src.get("private_key_path_value") or "").strip()
    if key_inline and Path(key_inline).is_file():
        key_path: str | None = key_inline
        key_pass = str(src.get("private_key_passphrase") or "").strip() or None
    else:
        pk_env = str(src.get("private_key_path_env") or "").strip()
        key_raw = os.environ.get(pk_env) if pk_env else None
        key_path = key_raw.strip() if key_raw else None
        key_pass_env = str(src.get("private_key_pass_env") or "").strip()
        key_pass = os.environ.get(key_pass_env) if key_pass_env else None

    transport = paramiko.Transport((host, port))
    try:
        if key_path and Path(key_path).is_file():
            pkey = paramiko.RSAKey.from_private_key_file(key_path, password=key_pass)
            transport.connect(username=username, pkey=pkey)
        else:
            if password is None:
                raise ValueError("SFTP password or private key required")
            transport.connect(username=username, password=password)
        client = paramiko.SFTPClient.from_transport(transport)
        if client is None:
            raise RuntimeError("SFTP client init failed")
        try:
            remote_path = src.get("remote_path")
            if remote_path:
                logger.info("SFTP get %s -> %s", remote_path, local_path)
                client.get(str(remote_path), str(local_path))
                return local_path

            remote_dir_spec = (str(src.get("remote_dir") or ".").strip() or ".").strip()
            parts = [p.strip() for p in re.split(r"[|;]+", remote_dir_spec) if p.strip()]
            remote_dir_candidates = parts if parts else ["."]
            seen_dirs: set[str] = set()
            uniq_dirs: list[str] = []
            for d in remote_dir_candidates:
                if d not in seen_dirs:
                    seen_dirs.add(d)
                    uniq_dirs.append(d)

            pattern = str(src.get("remote_pattern") or "*")
            listings: dict[str, list[str]] = {}
            list_errors: dict[str, str] = {}
            chosen_dir: str | None = None
            best_name: str | None = None
            best_mtime = -1.0

            for remote_dir in uniq_dirs:
                reg_files: list[str] = []
                try:
                    attrs = client.listdir_attr(remote_dir)
                except OSError as exc:
                    list_errors[remote_dir] = str(exc)
                    listings[remote_dir] = []
                    continue
                dir_best: str | None = None
                dir_mtime = -1.0
                for attr in attrs:
                    if not S_ISREG(attr.st_mode):
                        continue
                    reg_files.append(attr.filename)
                    if fnmatch.fnmatch(attr.filename, pattern) and attr.st_mtime > dir_mtime:
                        dir_mtime = float(attr.st_mtime)
                        dir_best = attr.filename
                reg_files.sort()
                listings[remote_dir] = reg_files
                if dir_best is not None and dir_mtime > best_mtime:
                    best_mtime = dir_mtime
                    best_name = dir_best
                    chosen_dir = remote_dir

            if not best_name or chosen_dir is None:
                lines: list[str] = []
                for rd in uniq_dirs:
                    if rd in list_errors:
                        lines.append(f"  {rd!r}: (cannot list: {list_errors[rd]})")
                        continue
                    names = listings.get(rd, [])
                    if not names:
                        lines.append(f"  {rd!r}: (no regular files)")
                        continue
                    preview = ", ".join(names[:30])
                    if len(names) > 30:
                        preview += f", … (+{len(names) - 30} more)"
                    lines.append(f"  {rd!r}: {preview}")
                msg = (
                    f"No file matching {pattern!r} on {host} (tried: {uniq_dirs}).\n"
                    + "Files seen per directory:\n"
                    + "\n".join(lines)
                    + "\nSet the correct folder in FMS **Remote directory**, or **Remote file path** to the full path. "
                    "Multiple folders: separate with | or ; (e.g. `.|outbound|/export`)."
                )
                raise FileNotFoundError(msg)

            remote_file = f"{chosen_dir.rstrip('/')}/{best_name}"
            logger.info("SFTP get %s -> %s", remote_file, local_path)
            client.get(remote_file, str(local_path))
            return local_path
        finally:
            client.close()
    finally:
        transport.close()


def fetch_ftp(src: dict[str, Any], project_root: Path, password: str | None) -> Path:
    config_port = int(src.get("port", 21))
    host, port = _normalize_host_port(str(src["host"]), config_port)
    username = str(src.get("username") or "")
    use_tls = bool(src.get("use_tls", False))
    local_path = _resolve_local_path(project_root, str(src["local_path"]))
    _ensure_parent(local_path)

    if password is None and username:
        raise ValueError("FTP password required when username is set")

    ftp_cls = FTP_TLS if use_tls else FTP
    ftp = ftp_cls()
    try:
        ftp.connect(host, port, timeout=60)
        ftp.login(username or "anonymous", password or "")
        if use_tls:
            ftp.prot_p()

        remote_path = src.get("remote_path")
        if remote_path:
            logger.info("FTP retr %s -> %s", remote_path, local_path)
            with open(local_path, "wb") as out:
                ftp.retrbinary(f"RETR {remote_path}", out.write)
            return local_path

        remote_dir = str(src.get("remote_dir") or ".")
        pattern = str(src.get("remote_pattern") or "*")
        ftp.cwd(remote_dir)
        names = [n for n in ftp.nlst() if fnmatch.fnmatch(n, pattern)]
        if not names:
            raise FileNotFoundError(
                f"No file matching {pattern!r} under {remote_dir!r} on {host}",
            )

        def mtime_key(name: str) -> float:
            try:
                resp = ftp.sendcmd(f"MDTM {name}")
                m = re.search(r"(\d{14})", resp)
                if m:
                    from datetime import datetime

                    return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").timestamp()
            except Exception:
                pass
            return 0.0

        best = max(names, key=mtime_key)
        logger.info("FTP retr %s/%s -> %s", remote_dir, best, local_path)
        with open(local_path, "wb") as out:
            ftp.retrbinary(f"RETR {best}", out.write)
        return local_path
    finally:
        try:
            ftp.quit()
        except Exception:
            pass


def _read_http_response_body(resp: Any) -> tuple[bytes, str | None]:
    body = resp.read()
    ctype: str | None = None
    try:
        ctype = resp.headers.get("Content-Type")
    except Exception:
        pass
    return body, ctype


def _body_looks_like_html(body: bytes) -> bool:
    """True if payload starts like an HTML document (shop page, login, error), not CSV."""
    if not body:
        return False
    head = body[:4096].lstrip().lower()
    if head.startswith(b"<!doctype") or head.startswith(b"<html"):
        return True
    if head.startswith(b"\xef\xbb\xbf"):
        return b"<!doctype" in body[:8192].lower() or b"<html" in body[:8192].lower()
    return False


def _reject_html_feed_url(url: str, body: bytes, content_type: str | None = None) -> None:
    if not _body_looks_like_html(body):
        return
    extra = ""
    if content_type and "html" in content_type.lower():
        extra = f" Content-Type: {content_type!r}."
    raise RuntimeError(
        f"Feed URL {url!r} returned HTML ({len(body)} bytes), not a data file.{extra} "
        "The link may be a storefront page that needs login or a token; use an export or API URL that returns CSV."
    )


def fetch_http(src: dict[str, Any], project_root: Path, password: str | None) -> Path:
    """GET a feed file from ``http_url`` (``http`` or ``https``). Optional Basic auth from ``username``/password."""
    raw_url = str(src.get("http_url") or "").strip()
    if not raw_url:
        raise ValueError("http_url is required for URL protocol")
    if not re.match(r"^https?://", raw_url, flags=re.I):
        raise ValueError("http_url must start with http:// or https://")
    local_path = _resolve_local_path(project_root, str(src["local_path"]))
    _ensure_parent(local_path)

    req = urllib.request.Request(raw_url, method="GET")
    req.add_header(
        "User-Agent",
        str(src.get("http_user_agent") or "B2B-FeedAggregator/1.0"),
    )
    user = str(src.get("username") or "").strip()
    if user and password:
        token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
        req.add_header("Authorization", f"Basic {token}")

    timeout = float(src.get("http_timeout_sec") or 120)
    body: bytes | None = None
    content_type: str | None = None
    is_https = raw_url.lower().startswith("https://")
    if is_https:
        ssl_tries: list[str] = []
        tls_contexts = _https_ssl_contexts()
        for idx, tls_ctx in enumerate(tls_contexts):
            try:
                with urllib.request.urlopen(req, timeout=timeout, context=tls_ctx) as resp:
                    body, content_type = _read_http_response_body(resp)
                if idx > 0:
                    logger.info(
                        "HTTPS OK for %s using SSL fallback profile %s/%s",
                        raw_url.split("?", 1)[0],
                        idx + 1,
                        len(tls_contexts),
                    )
                break
            except urllib.error.HTTPError:
                raise
            except urllib.error.URLError as exc:
                reason = getattr(exc, "reason", None)
                if isinstance(reason, ssl.SSLError):
                    ssl_tries.append(str(reason))
                    continue
                raise RuntimeError(f"URL error for {raw_url!r}: {exc}") from exc
        if body is None:
            raise RuntimeError(
                f"HTTPS failed for {raw_url!r} after trying cert bundle + legacy TLS options. "
                f"Install `certifi` (pip install -r requirements.txt) if missing; "
                f"set FEED_HTTP_SSL_LEGACY=1 to prefer legacy profiles first; "
                f"last resort for broken PKI: FEED_HTTP_SSL_NO_VERIFY=1 in .env (insecure). "
                f"Or use SFTP. SSL errors: {' | '.join(ssl_tries)}",
            )
    else:
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body, content_type = _read_http_response_body(resp)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code} fetching {raw_url!r}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"URL error for {raw_url!r}: {exc}") from exc

    if not body:
        raise RuntimeError(f"Empty response from {raw_url!r}")
    _reject_html_feed_url(raw_url, body, content_type)
    local_path.write_bytes(body)
    logger.info("HTTP GET %s -> %s (%s bytes)", raw_url, local_path, len(body))
    return local_path


def _imap_body_attachment(
    msg: Any,
    extensions: tuple[str, ...],
) -> tuple[bytes, str] | None:
    from email.header import decode_header

    exts_norm = tuple(e.lower() if e.startswith(".") else f".{e.lower()}" for e in extensions)
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue
        fn = part.get_filename()
        if not fn:
            disp = str(part.get("Content-Disposition") or "")
            if "attachment" not in disp.lower():
                continue
            continue
        bits, enc = decode_header(fn)[0]
        if isinstance(bits, bytes):
            fn = bits.decode(enc or "utf-8", errors="replace")
        else:
            fn = str(bits)
        fn_lower = fn.lower()
        if not any(fn_lower.endswith(ext) for ext in exts_norm):
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        return payload, fn
    return None


def fetch_imap(src: dict[str, Any], project_root: Path, password: str) -> Path:
    host = str(src["imap_host"])
    user = str(src["imap_user"])
    folder = str(src.get("imap_folder", "INBOX"))
    local_path = _resolve_local_path(project_root, str(src["local_path"]))
    _ensure_parent(local_path)
    exts = tuple(str(x).lower() if str(x).startswith(".") else f".{x}" for x in src.get("attachment_extensions", [".csv"]))
    subject_needle = str(src.get("subject_contains") or "")
    sender_needle = str(src.get("sender_contains") or "")
    unseen_only = bool(src.get("search_unseen_only", True))

    M: imaplib.IMAP4_SSL | None = None
    try:
        M = imaplib.IMAP4_SSL(host, port=int(src.get("imap_port", 993)))
        M.login(user, password)
        M.select(folder)

        def _imap_search_ids(criterion: str) -> list[bytes]:
            typ, data = M.search(None, criterion)
            if typ != "OK":
                raise RuntimeError(f"IMAP SEARCH {criterion!r} failed: {typ} {data!r}")
            if not data or not data[0]:
                return []
            return data[0].split()

        ids: list[bytes] = _imap_search_ids("UNSEEN" if unseen_only else "ALL")
        if not ids and unseen_only:
            logger.info(
                "IMAP: no UNSEEN messages in %r; retrying with ALL (includes already-read mail)",
                folder,
            )
            ids = _imap_search_ids("ALL")
        if not ids:
            raise FileNotFoundError(
                "IMAP: no messages in folder "
                f"{folder!r} on {host!r}. If feeds are only in unread mail, leave "
                '"Unseen only" enabled; if the vendor email was already opened, either '
                "disable that option or mark a fresh copy unread. "
                "Also confirm the host is IMAP (often imap.*), not POP."
            )
        ids.reverse()
        picked: tuple[bytes, str] | None = None
        for msg_id in ids:
            typ, msg_data = M.fetch(msg_id, "(RFC822)")
            if typ != "OK" or not msg_data or not msg_data[0]:
                continue
            blob = msg_data[0]
            raw = blob[1] if isinstance(blob, tuple) else blob
            if not isinstance(raw, (bytes, bytearray)):
                continue
            msg = message_from_bytes(bytes(raw))
            if subject_needle:
                subj = str(msg.get("Subject") or "")
                if subject_needle.lower() not in subj.lower():
                    continue
            if sender_needle:
                frm = str(msg.get("From") or "")
                if sender_needle.lower() not in frm.lower():
                    continue
            att = _imap_body_attachment(msg, exts)
            if att:
                picked = att
                if bool(src.get("mark_seen", True)):
                    M.store(msg_id, "+FLAGS", "\\Seen")
                break
        if not picked:
            raise FileNotFoundError(
                "IMAP: no matching attachment "
                f"({', '.join(exts)}) in searched messages",
            )
        body, att_name = picked
        inner_pat = str(src.get("zip_inner_pattern") or "*.csv")
        if att_name.lower().endswith(".zip") or (len(body) >= 4 and body[:4] == _ZIP_MAGIC):
            if _zip_is_xlsx(body):
                _xlsx_bytes_to_csv_file(local_path, body)
                logger.info("IMAP converted XLSX %s -> %s", att_name, local_path)
                return local_path
            inner = zip_pick_inner_bytes(body, inner_pat)
            local_path.write_bytes(inner)
            logger.info("IMAP unpacked ZIP %s -> %s", att_name, local_path)
            return local_path

        local_path.write_bytes(body)
        logger.info("IMAP saved attachment %s -> %s", att_name, local_path)
        return local_path
    finally:
        if M is not None:
            try:
                M.logout()
            except Exception:
                pass


def fetch_source(src: dict[str, Any], project_root: Path) -> Path:
    protocol = str(src.get("protocol", "sftp")).strip().lower()
    pwd_env = str(src.get("password_env") or "")
    password: str | None = None
    inline_pw = src.get("password")
    if inline_pw is not None and str(inline_pw).strip() != "":
        password = str(inline_pw)
    elif pwd_env:
        password = os.environ.get(pwd_env)

    if protocol in ("sftp", "scp"):
        p = fetch_sftp(src, project_root, password)
        finalize_local_feed_file(p, src)
        return p
    if protocol in ("ftp", "ftps"):
        use_tls = protocol == "ftps" or bool(src.get("use_tls", False))
        src = {**src, "use_tls": use_tls}
        p = fetch_ftp(src, project_root, password)
        finalize_local_feed_file(p, src)
        return p
    if protocol in ("imap", "email", "e-mail"):
        if password is None or password == "":
            hint = f" env {pwd_env!r}" if pwd_env else " (set password in FMS or env)"
            raise ValueError("IMAP requires a password" + hint)
        p = fetch_imap(src, project_root, password)
        finalize_local_feed_file(p, src)
        return p
    if protocol in ("url", "http", "https"):
        p = fetch_http(src, project_root, password)
        finalize_local_feed_file(p, src)
        return p
    raise ValueError(f"Unknown protocol {protocol!r}; use sftp, ftp, ftps, imap, or url")
