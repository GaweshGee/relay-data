"""Process pending requests/*.json -> results/. Runs inside GitHub Actions.

Request : requests/<id>.json  {"url": "https://...", "render": false}
Result  : results/<id>.json (metadata, written LAST = done marker)
          results/<id>.html + results/<id>.txt   (pages)
          results/<id>.<ext>                      (other content)
Usage   : python scripts/relay.py [--needs-render]
"""
import asyncio
import ipaddress
import json
import pathlib
import re
import socket
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

REQ = pathlib.Path("requests")
RES = pathlib.Path("results")
MAX_BYTES = 5_000_000
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+\.json$")
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")


def pending():
    RES.mkdir(exist_ok=True)
    return [p for p in sorted(REQ.glob("*.json"))
            if SAFE_NAME.match(p.name) and not (RES / p.name).exists()]


def host_is_safe(host):
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0].split("%")[0])
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified):
            return False
    return True


async def url_is_safe(url):
    if url.startswith(("data:", "blob:")):
        return True
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    return await asyncio.to_thread(host_is_safe, p.hostname)


async def fetch_http(url):
    async with httpx.AsyncClient(timeout=30, headers={"User-Agent": UA}) as c:
        for _ in range(6):
            if not await url_is_safe(url):
                raise ValueError("blocked url (non-public or invalid)")
            async with c.stream("GET", url) as r:
                if r.is_redirect and r.headers.get("location"):
                    url = str(httpx.URL(url).join(r.headers["location"]))
                    continue
                buf, truncated = bytearray(), False
                async for chunk in r.aiter_bytes():
                    buf += chunk
                    if len(buf) > MAX_BYTES:
                        truncated = True
                        break
                return (r.status_code, url, r.headers.get("content-type", ""),
                        bytes(buf[:MAX_BYTES]), truncated)
        raise ValueError("too many redirects")


async def fetch_render(url):
    from playwright.async_api import async_playwright
    if not await url_is_safe(url):
        raise ValueError("blocked url (non-public or invalid)")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=["--no-sandbox"])
        try:
            page = await (await browser.new_context(user_agent=UA)).new_page()

            async def guard(route):
                if await url_is_safe(route.request.url):
                    await route.continue_()
                else:
                    await route.abort()

            await page.route("**/*", guard)
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=45000)
            try:
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            html = (await page.content()).encode()
            return (resp.status if resp else None, page.url,
                    "text/html; charset=utf-8", html[:MAX_BYTES],
                    len(html) > MAX_BYTES)
        finally:
            await browser.close()


def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    return re.sub(r"\n\s*\n+", "\n\n", soup.get_text("\n")).strip()


def ext_for(ctype, body):
    c = ctype.lower()
    if "html" in c or body[:200].lstrip().lower().startswith((b"<!doctype html", b"<html")):
        return "html"
    if "javascript" in c or "ecmascript" in c:
        return "js"
    if "css" in c:
        return "css"
    if "json" in c:
        return "json.txt"
    if "xml" in c:
        return "xml"
    if c.startswith("text/"):
        return "txt"
    if "pdf" in c:
        return "pdf"
    if "png" in c:
        return "png"
    if "jpeg" in c or "jpg" in c:
        return "jpg"
    return "bin"


async def process(path):
    rid = path.stem
    meta = {"id": rid, "fetched_at": datetime.now(timezone.utc).isoformat()}
    written = []
    try:
        req = json.loads(path.read_text())
        url, render = req["url"], bool(req.get("render", False))
        meta.update(url=url, render=render)
        fetch = fetch_render if render else fetch_http
        status, final, ctype, body, trunc = await fetch(url)
        ext = ext_for(ctype, body)
        meta.update(status=status, final_url=final, content_type=ctype,
                    bytes=len(body), truncated=trunc)
        files = {f"{rid}.{ext}": body}
        if ext == "html":
            files[f"{rid}.txt"] = html_to_text(body).encode()
        for name, data in files.items():
            (RES / name).write_bytes(data)
            written.append(name)
    except Exception as e:  # noqa: BLE001
        meta["error"] = f"{type(e).__name__}: {e}"
    meta["files"] = written
    (RES / f"{rid}.json").write_text(json.dumps(meta, indent=2))
    print(rid, "ERROR " + meta["error"] if "error" in meta else f"ok {meta['status']}")


def needs_render():
    for p in pending():
        try:
            if json.loads(p.read_text()).get("render"):
                return True
        except Exception:  # noqa: BLE001
            pass
    return False


async def main():
    for p in pending():
        await process(p)


if __name__ == "__main__":
    if "--needs-render" in sys.argv:
        print("true" if needs_render() else "false")
    else:
        asyncio.run(main())
