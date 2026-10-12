# relay-data
Request/result store for the fetch relay.

Add `requests/<id>.json`:
```json
{"url": "https://example.com", "render": false}
```
Set `"render": true` for JavaScript-heavy pages (uses a headless browser).
Results appear in `results/<id>.json` (metadata), plus `<id>.html` / `<id>.txt` etc.
