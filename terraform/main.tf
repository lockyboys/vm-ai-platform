# terraform/main.tf ★ 7.12.0
# ⭐ GCP 클라우드 인프라 자동 생성
# 초등학생 설명: 이 파일 하나로 구글 클라우드에 서버를 자동으로 만들어요!
# 🆕 7.12.0: SERVER_HOST 변수 추가 — IP 자동 출력

terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}

# ── 변수 정의 ────────────────────────────────────────────
variable "project_id" {
  description = "GCP 프로젝트 ID"
  type        = string
}

variable "region" {
  description = "서버 지역 (서울)"
  type        = string
  default     = "asia-northeast3"
}

variable "zone" {
  description = "서버 존"
  type        = string
  default     = "asia-northeast3-a"
}

# 🆕 서버 이름 변수 — config.py SERVER_HOST와 연동
variable "instance_name" {
  description = "VM 인스턴스 이름"
  type        = string
  default     = "vm-project-7.12.0"
}

# ── VM 서버 생성 ─────────────────────────────────────────
resource "google_compute_instance" "ai_server" {
  name         = var.instance_name
  machine_type = "n2-standard-4"   # 4 CPU, 16GB RAM
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 100
    }
  }

  network_interface {
    network = "default"
    access_config {}   # 공개 IP 자동 할당
  }

  metadata_startup_script = file("${path.module}/startup.sh")
  tags = ["ai-server", "http-server"]
}

# ── 방화벽 규칙 ──────────────────────────────────────────
resource "google_compute_firewall" "ai_firewall" {
  name    = "vm-7.12.0-firewall"
  network = "default"

  allow {
    protocol = "tcp"
    # 🆕 7.12.0: 8000(Flask), 27017(MongoDB), 3306(MariaDB) 포트 허용
    ports = ["8000", "27017", "3306", "6379", "9092"]
  }

  source_ranges = ["0.0.0.0/0"]
  target_tags   = ["ai-server"]
}

# ── 출력 ─────────────────────────────────────────────────
# 🆕 IP를 출력해서 config.py SERVER_HOST에 복사하기 편하게!
output "server_ip" {
  description = "AI 서버 외부 IP (config.py SERVER_HOST에 복사하세요!)"
  value       = google_compute_instance.ai_server.network_interface[0].access_config[0].nat_ip
}

output "dashboard_url" {
  description = "대시보드 접속 주소"
  value       = "http://${google_compute_instance.ai_server.network_interface[0].access_config[0].nat_ip}:8000"
}
