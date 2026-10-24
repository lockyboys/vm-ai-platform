import httpx
import jwt
from datetime import datetime, timezone, timedelta

# 우리가 알고 있는 최선의 정보로 토큰 생성
payload = {
    "sub": "jeaje", "name": "jeaje", "user_id": "jeaje", 
    "role": "admin", "iss": "sps", "aud": "sps", "type": "access",
    "exp": datetime.now(timezone.utc) + timedelta(hours=1)
}
token = jwt.encode(payload, "luckyboys-master-key-2026", algorithm="HS256")

url = "https://subprime-glowworm-mundane.ngrok-free.dev/mcp"
headers = {
    "Authorization": f"Bearer {token}",
    "ngrok-skip-browser-warning": "true"
}

print("[*] 서버 보안망 찌르기 시도...")
try:
    res = httpx.post(url, headers=headers, timeout=5)
    print(f"🔥 [서버의 거절 사유] HTTP {res.status_code}")
    print(f"🔥 [상세 메시지] {res.text}")
except Exception as e:
    print(f"[접속 실패] {e}")
