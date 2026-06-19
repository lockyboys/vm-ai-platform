# web/app.py ★ 7.20.0
# ⭐ Flask API 서버 — 권한 체크 완전 적용
# 🆕 free=분류만 / pro=배치처리포함 / enterprise=전부
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, render_template, request, send_file, abort
from werkzeug.utils import secure_filename
from utils import logger, read_csv_safe, file_hash, read_file_auto, get_excel_sheets
from services.history_service import (
    save_login_history, save_upload_history, save_deploy_history,
    load_history, load_all_history, get_stats
)
from config import API_HOST, API_PORT, DEBUG, UPLOAD_PATH, OUTPUT_PATH, MODEL_VERSION
from services.auth.auth_service import (
    check_permission, check_learning_permission,
    get_all_permissions, get_permission_summary,
    get_upgrade_info, ENTERPRISE_HIGHLIGHTS,
    create_token, hash_password
)

ALLOWED_EXT = {"csv", "xlsx", "xls", "tsv"}
from src.AI.controllers.ai_job_controller import ai_job_bp

app = Flask(__name__)
app.register_blueprint(ai_job_bp)
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50MB

# 🆕 config의 서버 주소/가격 정보를 모든 템플릿에 전역 주입
# 초등학생 설명: 모든 웹 페이지가 서버 주소·가격을 자동으로 알게 해줘요!
# IP나 가격 바꾸려면 config.py만 수정하면 돼요!
from config import SERVER_BASE_URL, SERVER_API_URL, SERVER_HOST, SERVER_PORT, PLAN_PRICES
app.jinja_env.globals.update(
    SERVER_BASE_URL = SERVER_BASE_URL,
    SERVER_API_URL  = SERVER_API_URL,
    SERVER_HOST     = SERVER_HOST,
    SERVER_PORT     = SERVER_PORT,
    PLAN_PRICES     = PLAN_PRICES,
    APP_VERSION     = MODEL_VERSION,
)

def allowed_file(fn): return "." in fn and fn.rsplit(".",1)[1].lower() in ALLOWED_EXT

def get_plan(req) -> str:
    """요청에서 플랜 추출 (토큰 또는 파라미터)"""
    # 실서비스: Authorization 헤더 → verify_token(token)["plan"]
    # 데모: plan 파라미터 직접 사용
    token = req.headers.get("Authorization","").replace("Bearer ","")
    if token:
        from services.auth.auth_service import verify_token
        info = verify_token(token)
        return info.get("plan","free")
    data = req.json if req.is_json else {}
    return data.get("plan", req.args.get("plan","free"))

def permission_error(plan: str, feature: str, msg: str = ""):
    """
    권한 없음 응답 — 업그레이드 UX 포함
    초등학생 설명: "이 기능은 못 써요! 대신 이렇게 하면 쓸 수 있어요" 알려줘요.
    """
    upgrade_info = get_upgrade_info(plan, feature)
    highlight    = ENTERPRISE_HIGHLIGHTS.get(feature, {})
    return jsonify({
        "error":         f"권한 없음: [{plan}] 플랜은 '{feature}' 사용 불가",
        "code":          403,
        "upgrade_info":  upgrade_info,
        "highlight":     highlight,
        # 프론트엔드에서 이 정보로 업그레이드 팝업을 띄워요!
        "cta":           upgrade_info.get("cta", ""),
        "upgrade_url":   upgrade_info.get("upgrade_url", "/register"),
    }), 403

# ── DB 초기화 ──────────────────────────────────────────
def init_app():
    from services.db.db_service import init_db
    init_db()


# ════════════════════════════════════════════════════════
# 📄 페이지 라우트 — 로그인 체크 포함
# ════════════════════════════════════════════════════════

@app.route("/")
def home():
    """메인 대시보드 — JS에서 토큰 없으면 /login 으로 자동 이동"""
    return render_template("index.html")

@app.route("/login")
def login_page():
    """로그인 페이지"""
    return render_template("login.html")

@app.route("/register")
def register_page():
    """회원가입 + 약관동의 + 플랜선택"""
    return render_template("register.html")

@app.route("/terms")
def terms_page():
    """서비스 약관 전문"""
    return render_template("terms.html")

@app.route("/logout")
def logout():
    """로그아웃 → 로그인 페이지"""
    return render_template("login.html")

@app.route("/demo")
def demo():
    """
    권한 시스템 데모 페이지
    초등학생 설명: 각 플랜이 어떤 기능을 쓸 수 있는지
                  직접 눌러보면서 확인할 수 있어요!
    접속: http://34.64.209.152:8000/demo
    """
    return render_template("demo.html")


# ════════════════════════════════════════════════════════
# 🔐 회원가입 / 로그인
# ════════════════════════════════════════════════════════
@app.route("/api/register", methods=["POST"])
def register():
    """회원가입 — plan 선택 포함"""
    data  = request.json or {}
    email = data.get("email","")
    pw    = data.get("password","")
    plan  = data.get("plan","free")

    if not email or not pw:
        return jsonify({"error":"email과 password 필요"}), 400
    if plan not in ("free","pro","enterprise"):
        return jsonify({"error":"plan은 free/pro/enterprise 중 하나"}), 400

    # DB 저장 (users 테이블)
    try:
        import mysql.connector
        from config import MYSQL_CONFIG
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO AU_USERS
            (
                login_id,
                user_name,
                email,
                password_hash,
                plan_code,
                is_active
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                UPPER(%s),
                TRUE
            )
            """,
            (email, email.split("@")[0], email, hash_password(pw), plan)
        )
        uid = cursor.lastrowid
        conn.commit(); cursor.close(); conn.close()
    except Exception as e:
        # DB 없어도 토큰은 발급 (데모용)
        uid = 1
        logger.warning(f"⚠️ DB 저장 실패(데모모드): {e}")

    token_info = create_token(str(uid), email, plan)
    logger.info(f"👤 회원가입: {email} [{plan}]")
    return jsonify({"success": True, **token_info,
                    "permissions": get_all_permissions(plan)})


@app.route("/api/login", methods=["POST"])
def login():
    """
    로그인 → JWT 토큰 발급
    초등학생 설명: 이메일+비밀번호 확인 후 입장권(토큰) 발급해요.
    DB에 있는 계정으로 로그인 가능하고,
    DB 연결 실패 시 데모 모드로 동작해요.

    기본 제공 테스트 계정:
        free@test.com       / test1234  → Free 플랜
        pro@test.com        / test1234  → Pro 플랜
        enterprise@test.com / test1234  → Enterprise 플랜
        admin@test.com      / admin1234 → Enterprise (관리자)
    """
    data  = request.json or {}
    email = data.get("email", "").strip()
    pw    = data.get("password", "")

    if not email or not pw:
        return jsonify({"error": "이메일과 비밀번호를 입력해주세요"}), 400

    try:
        # DB에서 사용자 조회
        from services.db.db_service import get_user_by_email
        import mysql.connector
        from config import MYSQL_CONFIG

        user = get_user_by_email(email)

        if not user:
            return jsonify({"error": "등록되지 않은 이메일이에요"}), 401

        if user["password"] != hash_password(pw):
            return jsonify({"error": "비밀번호가 틀렸어요"}), 401

        if not user.get("is_active", 1):
            return jsonify({"error": "비활성화된 계정이에요"}), 401

        # 마지막 로그인 시각 업데이트
        try:
            conn   = mysql.connector.connect(**MYSQL_CONFIG)
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE AU_USERS SET updated_at=NOW() WHERE email=%s", (email,)
            )
            conn.commit(); cursor.close(); conn.close()
        except Exception:
            pass

        plan       = user["plan"]
        token_info = create_token(str(user["id"]), email, plan)
        logger.info(f"🔐 로그인 성공: {email} [{plan}]")
        save_login_history(email, plan, True)   # 🆕 JSON 이력 저장

        return jsonify({
            "success":     True,
            "email":       email,
            "plan":        plan,
            "permissions": get_all_permissions(plan),
            **token_info,
        })

    except Exception as e:
        logger.warning(f"⚠️ DB 로그인 실패 → 데모 모드: {e}")
        # DB 연결 실패 시 데모 모드 (샘플 계정 직접 확인)
        DEMO_ACCOUNTS = {
            "free@test.com":       ("test1234",  "free"),
            "pro@test.com":        ("test1234",  "pro"),
            "enterprise@test.com": ("test1234",  "enterprise"),
            "admin@test.com":      ("admin1234", "enterprise"),
        }
        if email in DEMO_ACCOUNTS:
            demo_pw, demo_plan = DEMO_ACCOUNTS[email]
            if pw == demo_pw:
                token_info = create_token("demo", email, demo_plan)
                return jsonify({
                    "success":     True,
                    "email":       email,
                    "plan":        demo_plan,
                    "demo_mode":   True,
                    "permissions": get_all_permissions(demo_plan),
                    **token_info,
                })
        return jsonify({"error": "로그인 실패 (DB 연결 확인 필요)"}), 401


# ════════════════════════════════════════════════════════
# 📡 상태 확인
# ════════════════════════════════════════════════════════
@app.route("/api/status")
def status():
    return jsonify({"status":"running","version":MODEL_VERSION,
                    "message":"AI 서버 정상 동작 중 🚀"})


# ════════════════════════════════════════════════════════
# 📤 파일 업로드 (free도 가능)
# ════════════════════════════════════════════════════════
@app.route("/api/upload", methods=["POST"])
def upload():
    """
    파일 업로드 — CSV / XLSX / XLS / TSV 모두 지원
    🆕 7.16.4: 엑셀 지원 + 학습방식 자동 추천 + 파일형식 반환
    """
    plan = get_plan(request)
    if not check_permission(plan, "CSV업로드"):
        return permission_error(plan, "CSV업로드")

    if "file" not in request.files:
        return jsonify({"error": "파일이 없어요"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "파일명이 없어요"}), 400

    # 확장자 체크
    ext = os.path.splitext(f.filename)[1].lower()
    if ext not in [".csv", ".xlsx", ".xls", ".tsv"]:
        return jsonify({"error": "CSV · XLSX · XLS · TSV 파일만 가능해요"}), 400

    force      = request.args.get("force","false").lower() == "true"
    sheet_name = request.form.get("sheet_name", 0)
    file_type  = ext.replace(".","").upper()

    filename  = secure_filename(f.filename)
    os.makedirs(UPLOAD_PATH, exist_ok=True)
    temp_path = os.path.join(UPLOAD_PATH, f"_tmp_{filename}")
    f.save(temp_path)

    try:
        fhash = file_hash(temp_path)

        # 중복 체크
        existing = _check_duplicate_file(fhash)
        if existing and not force and os.path.exists(existing.get("save_path","")):
            os.remove(temp_path)

            # 기존 파일 읽어서 컬럼정보/추천도 반환
            try:
                df_ex    = read_file_auto(existing["save_path"])
                from core.target_detector import get_column_info
                col_info = get_column_info(df_ex)
                from core.learning_recommender import recommend_learning_type as _rec
                recommend = _rec(df_ex)
            except Exception:
                col_info  = {}
                recommend = {"recommended":"supervised","confidence":50,"reason":""}

            return jsonify({
                "success":   True,
                "duplicate": True,
                "message":   f"이미 업로드된 파일이에요! 기존 파일을 사용해요.",
                "filename":  existing["filename"],
                "file_path": existing["save_path"],
                "file_hash": fhash,
                "파일형식":  file_type,
                "행수":      existing.get("row_count", 0),
                "열수":      existing.get("col_count", 0),
                "업로드일":  str(existing.get("uploaded_at","")),
                "컬럼정보":  col_info,
                "추천":      recommend,
                "시트목록":  [],
            })

        # 정식 저장
        save_path = os.path.join(UPLOAD_PATH, filename)
        if os.path.exists(save_path) and file_hash(save_path) != fhash:
            name, e2 = os.path.splitext(filename)
            filename  = f"{name}_{fhash[:6]}{e2}"
            save_path = os.path.join(UPLOAD_PATH, filename)

        os.rename(temp_path, save_path)

        # 엑셀 시트 목록
        sheets = []
        if ext in [".xlsx", ".xls"]:
            sheets = get_excel_sheets(save_path)
            try:
                sheet_name = int(sheet_name)
            except (ValueError, TypeError):
                pass

        # 파일 읽기
        df = read_file_auto(save_path, sheet_name)

        # 컬럼 정보
        from core.target_detector import get_column_info
        col_info = get_column_info(df)

        # 학습방식 추천
        try:
            from core.learning_recommender import recommend_learning_type as _rec
            recommend = _rec(df)
        except Exception as e2:
            logger.warning(f"⚠️ 추천 실패: {e2}")
            recommend = {"recommended":"supervised","confidence":50,"reason":"자동 추천 불가","all_scores":{}}

        # 이력 저장
        save_upload_history(plan, filename, fhash, len(df), len(df.columns))
        _save_upload_record(plan, filename, save_path, fhash, len(df), len(df.columns), col_info)

        logger.info(f"📤 업로드 완료: [{file_type}] {filename} ({len(df)}행)")

        return jsonify({
            "success":   True,
            "duplicate": False,
            "filename":  filename,
            "file_path": save_path,
            "file_hash": fhash,
            "파일형식":  file_type,
            "시트목록":  sheets,
            "현재시트":  sheet_name,
            "행수":      len(df),
            "열수":      len(df.columns),
            "컬럼정보":  col_info,
            "추천":      recommend,
        })

    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        logger.error(f"❌ 업로드 실패: {e}")
        return jsonify({"error": f"파일 처리 실패: {str(e)}"}), 500


# ════════════════════════════════════════════════════════
# ▶ AI 분석 실행
# ════════════════════════════════════════════════════════
@app.route("/api/run", methods=["POST"])
def run_ai_analysis():
    """
    업로드한 파일로 AI 분석 실행
    초등학생 설명: 왼쪽에서 올린 파일을 가지고 AI가 공부하고 결과를 만들어줘요!
    DB는 지우지 않고 결과만 새로 저장해요.
    """
    data = request.json or {}
    plan = get_plan(request)

    # 기본 AI 분석 권한 확인
    if not check_permission(plan, "AI분석"):
        return permission_error(plan, "AI분석")

    file_path     = data.get("file_path")
    target_col    = data.get("target_col")
    feature_cols  = data.get("feature_cols")
    learning_type = data.get("learning_type", "supervised")
    user_id       = data.get("user_id", "dashboard_user")

    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "분석할 파일이 없어요. 먼저 업로드해 주세요."}), 400

    # feature_cols는 화면에서 "a,b,c" 문자열로 올 수 있어서 리스트로 바꿔요.
    if isinstance(feature_cols, str):
        feature_cols = [x.strip() for x in feature_cols.split(",") if x.strip()]

    try:
        # 태스크 유형을 먼저 가볍게 확인해서 Free는 분류만 허용해요.
        df_preview = read_file_auto(file_path)
        from core.target_detector import find_target, get_task_type
        target_for_check = target_col or find_target(df_preview)
        task_type = get_task_type(df_preview, target_for_check)

        ok, need_perm, msg = check_learning_permission(plan, learning_type, task_type)
        if not ok:
            return permission_error(plan, need_perm, msg)

        from pipeline import run_pipeline
        result = run_pipeline(
            file_path=file_path,
            user_id=user_id,
            target_col=target_col,
            feature_cols=feature_cols,
            learning_type=learning_type,
        )
        return jsonify(result)
    except Exception as e:
        logger.error(f"❌ AI 분석 실패: {e}")
        return jsonify({"error": f"AI 분석 실패: {str(e)}"}), 500


@app.route("/api/download/<path:filename>")
def download_file(filename):
    """
    결과 파일 다운로드
    초등학생 설명: 서버가 만든 PDF/차트 파일을 내 컴퓨터로 내려받아요.
    """
    plan = get_plan(request)
    if not check_permission(plan, "파일다운로드") and not check_permission(plan, "PDF다운로드"):
        return permission_error(plan, "파일다운로드")

    # outputs/reports, outputs/charts에서만 찾도록 제한해요. 임의 경로 다운로드 방지!
    for folder in ["reports", "charts", "shap", "exports"]:
        fp = os.path.join(OUTPUT_PATH, folder, filename)
        if os.path.exists(fp):
            return send_file(fp, as_attachment=True)
    return jsonify({"error": "파일을 찾을 수 없어요"}), 404


@app.route("/api/files")
def list_files():
    plan = get_plan(request)
    if not check_permission(plan, "결과조회"):
        return permission_error(plan, "결과조회")

    files = []
    for cat, folder in [("리포트","reports"),("차트","charts")]:
        d = os.path.join(OUTPUT_PATH, folder)
        if os.path.exists(d):
            for fn in sorted(os.listdir(d), reverse=True)[:20]:
                fp = os.path.join(d, fn)
                can_dl = check_permission(plan,"파일다운로드")
                files.append({
                    "카테고리": cat, "파일명": fn,
                    "크기": os.path.getsize(fp),
                    "다운로드가능": can_dl,
                    "다운로드URL": f"/api/download/{fn}" if can_dl else None,
                })
    return jsonify({"files": files})


# ════════════════════════════════════════════════════════
# 📊 모델 히스토리 / 권한 / Cron
# ════════════════════════════════════════════════════════
@app.route("/api/history")
def history():
    """
    모델 정확도 히스토리 — JSON 파일 우선, DB 보조
    초등학생 설명: AI가 지금까지 공부한 성적표를 보여줘요!
    """
    # JSON 파일에서 먼저 조회 (항상 있음)
    json_history = load_history("model", days=30, limit=50)
    if json_history:
        return jsonify({"history": json_history, "source": "json"})
    # JSON 없으면 DB에서 조회
    from services.db.db_service import get_model_history
    return jsonify({"history": get_model_history(50), "source": "db"})


@app.route("/api/history/all")
def history_all():
    """
    전체 카테고리 이력 JSON 조회
    초등학생 설명: 모든 종류의 기록을 한번에 볼 수 있어요!
    """
    days = int(request.args.get("days", 7))
    return jsonify(load_all_history(days=days))


@app.route("/api/history/<category>")
def history_by_category(category):
    """
    카테고리별 이력 조회
    category: pipeline / model / cron / upload / login / deploy
    """
    allowed = ["pipeline","model","cron","upload","login","deploy"]
    if category not in allowed:
        return jsonify({"error": f"허용된 카테고리: {allowed}"}), 400
    days  = int(request.args.get("days",  7))
    limit = int(request.args.get("limit", 50))
    return jsonify({
        "category": category,
        "history":  load_history(category, days=days, limit=limit),
    })


@app.route("/api/stats")
def stats():
    """
    전체 이력 통계 요약
    초등학생 설명: "이번 주에 뭘 얼마나 했는지" 요약해줘요!
    """
    days = int(request.args.get("days", 7))
    return jsonify(get_stats(days=days))


# ════════════════════════════════════════════════════════
# ⏰ Cron 관리 API (Pro=조회만 / Enterprise=전체)
# ════════════════════════════════════════════════════════
@app.route("/api/cron/status")
def cron_status():
    """
    Cron 실행 이력 조회 — Pro 이상 허용
    초등학생 설명: "언제 자동 학습이 됐는지" 기록을 볼 수 있어요!
    Pro는 조회만, Enterprise는 등록/수정/삭제까지 가능해요.
    """
    plan = get_plan(request)

    # Pro는 조회만, Enterprise는 전체
    if not check_permission(plan, "Cron조회") and        not check_permission(plan, "Cron관리"):
        return permission_error(plan, "Cron조회")

    try:
        import mysql.connector
        from config import MYSQL_CONFIG
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM cron_logs ORDER BY ran_at DESC LIMIT 20"
        )
        logs = cursor.fetchall()
        cursor.close(); conn.close()
    except Exception:
        # DB 연결 안 될 때 로그 파일에서 대체
        import glob, json as _json
        from config import LOG_PATH
        logs = []
        for f in sorted(glob.glob(
            os.path.join(LOG_PATH, "cron_*.json")
        ), reverse=True)[:10]:
            try:
                logs.append(_json.load(open(f)))
            except Exception:
                pass

    return jsonify({
        "plan":        plan,
        "cron_logs":   logs,
        "can_manage":  check_permission(plan, "Cron관리"),   # 관리 권한 여부
        "can_view":    True,
    })


@app.route("/api/cron/trigger", methods=["POST"])
def cron_trigger():
    """
    Cron 수동 실행 — Enterprise만 허용
    초등학생 설명: "지금 당장 자동 학습 실행해줘!" 명령이에요.
    Enterprise 회원만 수동으로 실행할 수 있어요.
    """
    plan = get_plan(request)
    if not check_permission(plan, "Cron관리"):
        return permission_error(plan, "Cron관리")

    job_name = (request.json or {}).get("job", "daily_retrain")

    try:
        if job_name == "daily_retrain":
            from scheduler.cron_jobs import job_daily_retrain
            import threading
            t = threading.Thread(target=job_daily_retrain)
            t.daemon = True
            t.start()
            return jsonify({"success": True, "message": "🔄 자동 재학습 시작됨!"})
        elif job_name == "self_improve":
            from scheduler.cron_jobs import job_self_improve
            job_self_improve()
            return jsonify({"success": True, "message": "🧠 자기개선 완료!"})
        else:
            return jsonify({"error": f"알 수 없는 작업: {job_name}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ════════════════════════════════════════════════════════
# 💳 업그레이드 UX API
# ════════════════════════════════════════════════════════
@app.route("/api/upgrade-info")
def upgrade_info():
    """
    업그레이드 안내 정보 반환
    초등학생 설명: "이 기능 쓰려면 얼마를 더 내야 해?" 알려줘요!
    프론트에서 업그레이드 팝업을 만들 때 이 데이터를 써요.
    """
    plan    = request.args.get("plan", "free")
    feature = request.args.get("feature", "")
    if not feature:
        return jsonify({"error": "feature 파라미터 필요"}), 400
    return jsonify(get_upgrade_info(plan, feature))


@app.route("/api/enterprise-highlights")
def enterprise_highlights():
    """
    Enterprise 차별 기능 마케팅 정보
    초등학생 설명: "Enterprise만 쓸 수 있는 특별한 기능들이에요!" 홍보해요.
    """
    return jsonify({
        "highlights": ENTERPRISE_HIGHLIGHTS,
        "count":      len(ENTERPRISE_HIGHLIGHTS),
    })

@app.route("/api/permissions")
def permissions():
    plan = request.args.get("plan","free")
    return jsonify({
        "plan":        plan,
        "permissions": get_all_permissions(plan),
        "summary":     get_permission_summary(),
    })

@app.route("/api/admin/set-plan", methods=["POST"])
def set_plan():
    """관리자 전용 — 플랜 변경"""
    plan = get_plan(request)
    if plan != "enterprise":
        return permission_error(plan, "관리자기능")
    data  = request.json or {}
    email = data.get("email","")
    new_plan = data.get("plan","free")
    try:
        import mysql.connector
        from config import MYSQL_CONFIG
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cur  = conn.cursor()
        cur.execute("UPDATE AU_USERS SET plan_code=UPPER(%s) WHERE email=%s", (new_plan, email))
        conn.commit(); cur.close(); conn.close()
        return jsonify({"success": True, "email": email, "new_plan": new_plan})
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@app.route("/mindmap")
def mindmap_page():
    """v7.20.0 최종 마인드맵 페이지"""
    return render_template("mindmap_v7.20.0.html")


# ════════════════════════════════════════════════════════
# ❌ 에러 핸들러
# ════════════════════════════════════════════════════════
@app.errorhandler(404)
def not_found(e):   return jsonify({"error":"없는 페이지","code":404}), 404
@app.errorhandler(500)
def server_err(e):  return jsonify({"error":"서버 오류","code":500}), 500
@app.errorhandler(413)
def too_large(e):   return jsonify({"error":"파일 너무 큼(최대 50MB)","code":413}), 413


# ════════════════════════════════════════════════════════
# 🔑 관리자 페이지 + API
# ════════════════════════════════════════════════════════
@app.route("/admin")
def admin_page():
    """
    관리자 대시보드 — Enterprise 권한 필요
    초등학생 설명: 관리자만 들어올 수 있는 특별한 방이에요!
    접속: http://34.64.209.152:8000/admin
    """
    return render_template("admin.html")


@app.route("/api/admin/users")
def admin_users():
    """전체 사용자 목록 조회 (관리자용)"""
    from services.db.db_service import get_all_users
    users = get_all_users()
    # datetime 직렬화
    for u in users:
        for k, v in u.items():
            if hasattr(v, 'isoformat'):
                u[k] = v.isoformat()
    return jsonify({"users": users, "count": len(users)})


@app.route("/api/admin/set-plan", methods=["POST"])
def admin_set_plan():
    """
    사용자 플랜 변경 (관리자용)
    초등학생 설명: 관리자가 회원의 등급을 바꿔줄 수 있어요!
    """
    data     = request.json or {}
    user_id  = data.get("user_id")
    new_plan = data.get("plan", "free")

    if new_plan not in ("free", "pro", "enterprise"):
        return jsonify({"error": "잘못된 플랜"}), 400

    try:
        import mysql.connector
        from config import MYSQL_CONFIG
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE AU_USERS SET plan_code=UPPER(%s) WHERE user_id=%s",
            (new_plan, user_id)
        )
        conn.commit(); cursor.close(); conn.close()
        logger.info(f"🔑 관리자 플랜 변경: user_id={user_id} → {new_plan}")
        return jsonify({"success": True, "user_id": user_id, "new_plan": new_plan})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/admin/deploy/upload", methods=["POST"])
def admin_deploy_upload():
    """
    배포용 ZIP 파일 업로드
    초등학생 설명: 새 버전 파일을 서버로 보내는 첫 단계예요!
    """
    if "zip" not in request.files:
        return jsonify({"error": "ZIP 파일 없음"}), 400

    f        = request.files["zip"]
    filename = secure_filename(f.filename)

    if not filename.endswith(".zip"):
        return jsonify({"error": "ZIP 파일만 가능"}), 400

    import tempfile
    deploy_path = os.path.join(tempfile.gettempdir(), filename)
    f.save(deploy_path)

    size = os.path.getsize(deploy_path)
    logger.info(f"📦 배포 ZIP 업로드: {filename} ({size/1024:.0f}KB)")
    return jsonify({"success": True, "filename": filename,
                    "path": deploy_path, "size": size})


@app.route("/api/admin/deploy/run", methods=["POST"])
def admin_deploy_run():
    """
    배포 실행 — launcher.sh 사용 (가장 안정적!)
    초등학생 설명: 미리 만들어둔 배포 스크립트를 실행해요!
    🆕 7.16.4: stdin 없이 자동 실행 (-f 플래그 사용)
    """
    import tempfile, subprocess, threading, shutil
    data     = request.json or {}
    filename = data.get("filename", "")
    version  = data.get("version", "unknown")

    zip_path    = os.path.join(tempfile.gettempdir(), filename)
    home_dir    = os.path.expanduser("~")
    install_dir = os.path.join(home_dir, "vm_project")
    backup_dir  = os.path.join(home_dir, "vm_backups")
    launcher    = os.path.join(home_dir, "launcher.sh")

    if not os.path.exists(zip_path):
        return jsonify({"error": "ZIP 파일 없음 — 먼저 업로드해주세요"}), 400

    def run_deploy():
        log_path = os.path.join(install_dir, "logs", "deploy.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)

        def log(msg):
            logger.info(msg)
            try:
                with open(log_path, "a", encoding="utf-8") as lf:
                    lf.write(msg + "\n")
            except Exception:
                pass

        try:
            log(f"🚀 배포 시작: v{version}")

            # launcher.sh 없으면 ZIP에서 추출
            if not os.path.exists(launcher):
                log("📥 launcher.sh 추출 중...")
                subprocess.run(
                    f"unzip -p {zip_path} vm_project/scripts/launcher.sh > {launcher}",
                    shell=True
                )
                os.chmod(launcher, 0o755)
                log("  ✅ launcher.sh 준비 완료")

            # 🆕 launcher.sh를 직접 Python subprocess로 단계별 실행
            # (yes 자동 응답 대신 Python이 직접 처리)
            log("📋 STEP 1: 기존 서버 종료")
            subprocess.run("pkill -f 'python3 run_server.py' 2>/dev/null; fuser -k 8000/tcp 2>/dev/null; sleep 1", shell=True)
            log("  ✅ 완료")

            log("💾 STEP 2: 백업")
            os.makedirs(backup_dir, exist_ok=True)
            from datetime import datetime
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            bak  = os.path.join(backup_dir, f"vm_project_backup_v{version}_{ts}.tar.gz")
            if os.path.exists(install_dir):
                subprocess.run(
                    f"tar -czf {bak} --exclude='*/logs/*' --exclude='*/__pycache__/*' "
                    f"-C {home_dir} vm_project 2>/dev/null",
                    shell=True
                )
                log(f"  ✅ 백업: {os.path.basename(bak)}")

                # 오래된 백업 정리 (최근 5개)
                import glob as _glob
                baks = sorted(_glob.glob(os.path.join(backup_dir,"*.tar.gz")))
                for old_bak in baks[:-5]:
                    os.remove(old_bak)

            log("🗑️ STEP 3: 기존 파일 삭제")
            if os.path.exists(install_dir):
                shutil.rmtree(install_dir)
            log("  ✅ 완료")

            log("📦 STEP 4: 새 버전 압축 해제")
            subprocess.run(f"cd {home_dir} && unzip -q {zip_path}", shell=True)

            # 폴더명 rename
            extracted = subprocess.run(
                f"unzip -Z1 {zip_path} 2>/dev/null | head -1 | cut -d'/' -f1",
                shell=True, capture_output=True, text=True
            ).stdout.strip()
            if extracted and extracted != "vm_project":
                src = os.path.join(home_dir, extracted)
                if os.path.exists(src):
                    os.rename(src, install_dir)
                    log(f"  📁 {extracted} → vm_project")
            log("  ✅ 완료")

            log("📁 STEP 5: 필수 폴더 생성")
            for d in ["logs","outputs/charts","outputs/reports","models","data","uploads","data_lake"]:
                os.makedirs(os.path.join(install_dir, d), exist_ok=True)
            subprocess.run(f"chmod +x {install_dir}/scripts/*.sh 2>/dev/null", shell=True)
            log("  ✅ 완료")

            log("📦 STEP 6: 패키지 설치")
            req = os.path.join(install_dir, "requirements.txt")
            if os.path.exists(req):
                result = subprocess.run(
                    f"pip3 install -r {req} --break-system-packages -q 2>&1 | tail -3",
                    shell=True, capture_output=True, text=True
                )
                log(f"  ✅ 완료")

            # launcher.sh 자동 업데이트
            new_launcher = os.path.join(install_dir, "scripts", "launcher.sh")
            if os.path.exists(new_launcher):
                shutil.copy(new_launcher, launcher)
                os.chmod(launcher, 0o755)
                log("  ✅ launcher.sh 업데이트")

            log("🌐 STEP 7: 서버 재시작")
            flask_log = os.path.join(install_dir, "logs", "flask.log")
            subprocess.Popen(
                f"cd {install_dir} && nohup python3 run_server.py > {flask_log} 2>&1",
                shell=True
            )

            import time; time.sleep(4)
            check = subprocess.run(
                "curl -s http://127.0.0.1:8000/api/status 2>/dev/null",
                shell=True, capture_output=True, text=True, timeout=5
            )
            if "version" in check.stdout:
                log(f"  ✅ 서버 정상: {check.stdout[:80]}")
            else:
                log(f"  ⚠️ 서버 확인 실패 — flask.log 확인 필요")

            save_deploy_history(version, "완료", "배포 성공", "admin")
            log(f"🎉 배포 완료! v{version}")

        except Exception as e:
            log(f"❌ 배포 실패: {e}")
            save_deploy_history(version, "실패", str(e), "admin")

    threading.Thread(target=run_deploy, daemon=True).start()
    save_deploy_history(version, "시작", f"파일: {filename}", "admin")

    return jsonify({
        "success": True,
        "message": f"v{version} 배포 시작! 잠시 후 재시작돼요.",
        "version": version,
        "log_url": "/api/admin/deploy/log",
    })



@app.route("/api/admin/deploy/log")
def admin_deploy_log():
    """배포 로그 실시간 조회"""
    log_path = os.path.expanduser("~/vm_project/logs/deploy.log")
    if not os.path.exists(log_path):
        return jsonify({"log": "배포 로그 없음", "lines": []})
    lines = open(log_path, encoding="utf-8").readlines()[-50:]
    return jsonify({"log": "".join(lines), "lines": [l.strip() for l in lines]})


@app.route("/api/admin/backups")
def admin_backups():
    """백업 파일 목록 조회"""
    import glob as _glob
    backup_dir = os.path.expanduser("~/vm_backups")
    backups    = []
    for f in sorted(_glob.glob(os.path.join(backup_dir, "*.tar.gz")), reverse=True)[:10]:
        stat = os.stat(f)
        backups.append({
            "name": os.path.basename(f),
            "size": f"{stat.st_size/1024:.0f}KB",
            "date": __import__('datetime').datetime.fromtimestamp(
                stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return jsonify({"backups": backups})


@app.route("/api/upload/sheet", methods=["POST"])
def upload_sheet():
    """
    엑셀 시트 변경 API
    초등학생 설명: 엑셀 탭을 바꾸면 그 탭 데이터로 새로 읽어줘요!
    """
    sheet_name = request.form.get("sheet_name", 0)
    file_path  = request.form.get("file_path", "")

    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "파일 없음"}), 400

    try:
        # 시트명 타입 처리
        try:
            sheet_name = int(sheet_name)
        except (ValueError, TypeError):
            pass

        df       = read_file_auto(file_path, sheet_name)
        from core.target_detector import get_column_info
        from core.learning_recommender import recommend_learning_type
        col_info = get_column_info(df)

        try:
            recommend = recommend_learning_type(df)
        except Exception:
            recommend = {"recommended": "supervised", "confidence": 50}

        return jsonify({
            "success":   True,
            "file_path": file_path,
            "현재시트":  sheet_name,
            "행수":      len(df),
            "열수":      len(df.columns),
            "컬럼정보":  col_info,
            "추천":      recommend,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500



def _check_duplicate_file(fhash: str) -> dict:
    """
    업로드 파일 중복 확인

    목적:
        같은 파일이 이미 업로드되었는지 file_hash 기준으로 확인한다.

    관련 테이블:
        DT_UPLOAD_FILES
        DT_DATASETS
    """
    try:
        import mysql.connector
        from config import MYSQL_CONFIG

        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                uf.upload_file_id AS id,
                uf.original_file_name AS file_name,
                uf.file_hash,
                uf.file_path AS save_path,
                d.row_count,
                d.column_count AS col_count,
                uf.created_at AS uploaded_at
            FROM DT_UPLOAD_FILES uf
            LEFT JOIN DT_DATASETS d
                ON d.dataset_id = uf.dataset_id
            WHERE uf.file_hash = %s
            ORDER BY uf.created_at DESC
            LIMIT 1
            """,
            (fhash,)
        )

        row = cursor.fetchone()
        cursor.close()
        conn.close()

        return dict(row) if row else None

    except Exception:
        return None


def _save_upload_record(user_id, filename, save_path,
                        fhash, row_count, col_count, col_info) -> None:
    """
    업로드 이력 저장

    목적:
        업로드된 파일 정보를 DT_DATASETS와 DT_UPLOAD_FILES에 저장한다.

    트랜잭션:
        DT_DATASETS 저장과 DT_UPLOAD_FILES 저장은 하나의 작업이다.
        둘 다 성공하면 COMMIT.
        하나라도 실패하면 ROLLBACK.

    관련 테이블:
        DT_DATASETS
        DT_UPLOAD_FILES
    """
    try:
        import mysql.connector
        from config import MYSQL_CONFIG

        conn = mysql.connector.connect(**MYSQL_CONFIG)
        conn.start_transaction()
        cursor = conn.cursor()

        try:
            cursor.execute(
                """
                INSERT INTO DT_DATASETS
                (
                    dataset_name,
                    file_name,
                    file_path,
                    row_count,
                    column_count,
                    uploaded_by,
                    is_active
                )
                VALUES
                (
                    %s, %s, %s, %s, %s, %s, TRUE
                )
                """,
                (filename, filename, save_path, row_count, col_count, user_id)
            )

            dataset_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO DT_UPLOAD_FILES
                (
                    dataset_id,
                    original_file_name,
                    stored_file_name,
                    file_path,
                    file_size,
                    file_hash,
                    mime_type,
                    uploaded_by
                )
                VALUES
                (
                    %s, %s, %s, %s, NULL, %s, NULL, %s
                )
                ON DUPLICATE KEY UPDATE
                    dataset_id = VALUES(dataset_id),
                    file_path = VALUES(file_path),
                    uploaded_by = VALUES(uploaded_by)
                """,
                (dataset_id, filename, filename, save_path, fhash, user_id)
            )

            conn.commit()

        except Exception:
            conn.rollback()
            raise

        finally:
            cursor.close()
            conn.close()

    except Exception as e:
        logger.warning(f"⚠️ 업로드 이력 저장 실패: {e}")


@app.route("/api/admin/restart", methods=["POST"])
def admin_restart():
    """
    서버 재시작 API
    초등학생 설명: 지금 서버를 껐다가 다시 켜줘요!
    """
    import subprocess, threading

    def do_restart():
        import time
        time.sleep(1)  # 응답 보낸 후 재시작
        subprocess.Popen(
            "pkill -f run_server.py; sleep 2; "
            "cd ~/vm_project && nohup python3 run_server.py > logs/flask.log 2>&1 &",
            shell=True
        )

    threading.Thread(target=do_restart, daemon=True).start()
    save_deploy_history("current", "재시작", "관리자 수동 재시작", "admin")
    return jsonify({"success": True, "message": "재시작 명령 전송됨"})


# 직접 web/app.py로 실행해도 모든 라우트가 등록된 뒤 서버가 켜지게 마지막에 둡니다.
if __name__ == "__main__":
    init_app()
    app.run(host=API_HOST, port=API_PORT, debug=DEBUG)




