-- =============================================================================
-- VM Project v7.20.0 안전 업그레이드 SQL
-- 초등학생 설명: 기존 책장을 버리지 않고, 필요한 칸만 더 붙이는 작업이에요.
-- 중요: DROP / TRUNCATE 명령이 없습니다. 기존 DB 데이터를 지우지 않습니다.
-- =============================================================================

CREATE TABLE IF NOT EXISTS plan_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL COMMENT '플랜이 바뀐 사용자 번호',
    email VARCHAR(255) NULL COMMENT '사용자 이메일',
    old_plan VARCHAR(50) NULL COMMENT '이전 플랜',
    new_plan VARCHAR(50) NOT NULL COMMENT '새 플랜',
    changed_by VARCHAR(255) NULL COMMENT '누가 바꿨는지',
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '바뀐 시간'
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NULL COMMENT '행동한 사용자',
    action VARCHAR(255) NOT NULL COMMENT '무슨 일을 했는지',
    detail_json MEDIUMTEXT NULL COMMENT '자세한 내용 JSON',
    ip_address VARCHAR(64) NULL COMMENT '접속 IP',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '기록 시간'
);

CREATE TABLE IF NOT EXISTS api_keys (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL COMMENT 'API 키 주인',
    key_name VARCHAR(100) NOT NULL COMMENT '키 이름',
    key_hash VARCHAR(255) NOT NULL COMMENT 'API 키 해시',
    is_active TINYINT(1) DEFAULT 1 COMMENT '사용 가능 여부',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '생성 시간'
);

-- users 테이블에 관리자 역할 칸이 없다면 추가합니다.
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user' COMMENT 'user/admin 같은 역할';
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin TINYINT(1) DEFAULT 0 COMMENT '관리자 여부';

-- 테스트 관리자 계정은 관리자 표시를 붙입니다. 계정이 없으면 아무 일도 안 일어나요.
UPDATE users SET role='admin', is_admin=1 WHERE email='admin@test.com';
