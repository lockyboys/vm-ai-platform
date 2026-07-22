#!/usr/bin/env bash
set -euo pipefail

cd /data/vm_project

: "${COMMON_MARIADB_HOST:?COMMON_MARIADB_HOST is required}"
: "${COMMON_MARIADB_PORT:?COMMON_MARIADB_PORT is required}"
: "${COMMON_MARIADB_USER:?COMMON_MARIADB_USER is required}"
: "${COMMON_MARIADB_PASSWORD:?COMMON_MARIADB_PASSWORD is required}"
: "${COMMON_MARIADB_DATABASE:?COMMON_MARIADB_DATABASE is required}"

MYSQL_PWD="${COMMON_MARIADB_PASSWORD}" mariadb   -h "${COMMON_MARIADB_HOST}"   -P "${COMMON_MARIADB_PORT}"   -u "${COMMON_MARIADB_USER}"   "${COMMON_MARIADB_DATABASE}"   < sql/runtime/database_role_harness_registration_20260722.sql
