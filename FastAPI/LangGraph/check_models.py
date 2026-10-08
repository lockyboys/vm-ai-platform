import os
import google.generativeai as genai
from dotenv import load_dotenv

# .env 파일에서 GOOGLE_API_KEY 로드
load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

print("🔍 내 API 키로 사용할 수 있는 Gemini 모델 목록:")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        # 'models/' 부분을 제외한 정확한 이름만 출력
        print(f"- {m.name.replace('models/', '')}")