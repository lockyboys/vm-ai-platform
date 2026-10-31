"""삼성화재 PDF 버튼과 파일 번호 매핑 확인 probe."""
import json
import urllib.request

URL = "https://www.samsungfire.com/sfmi/ui/etcsv/info/productListHandler_new.js?v=20240124"
def main():
    req = urllib.request.Request(URL, headers={"User-Agent":"SPS-SamsungFire-Mapping-Probe/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        text = r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    lines = text.splitlines()
    needles = ("prdfilename", "for (var pi", "pdfCnt", "case 1", "fileDownload")
    out = []
    for i, line in enumerate(lines):
        if any(n.lower() in line.lower() for n in needles):
            out.extend(f"{j+1}: {lines[j].strip()}" for j in range(max(0,i-4), min(len(lines),i+5)))
    print(json.dumps({"lines": list(dict.fromkeys(out))}, ensure_ascii=False, indent=2))
if __name__ == "__main__":
    main()
