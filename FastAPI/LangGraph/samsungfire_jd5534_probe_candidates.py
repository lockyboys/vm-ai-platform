from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json

base = "https://www.samsungfire.com/publication/pdf/JD5534_0_"
candidates = [f"{base}20250101_file{i}.pdf" for i in range(1, 6)]
candidates += [f"{base}{date}_file1.pdf" for date in ("20240101", "20240701", "20260101", "20260701")]
out = []
for url in candidates:
    try:
        with urlopen(Request(url, headers={"User-Agent": "SPS-SamsungFire-Terms-Downloader/1.0"}), timeout=20) as r:
            head = r.read(5)
            out.append({"url": url, "status": r.status, "content_type": r.headers.get("Content-Type", ""), "pdf": head == b"%PDF", "bytes": r.headers.get("Content-Length")})
    except HTTPError as exc:
        out.append({"url": url, "status": exc.code})
    except URLError as exc:
        out.append({"url": url, "error": str(exc.reason)})
print(json.dumps(out, ensure_ascii=False, indent=2))
