#!/usr/bin/env bash
set -Eeuo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

WAIT_TIMEOUT="${WAIT_TIMEOUT:-300}"
SETTLE="${SETTLE:-3}"
MODES="monolith microservices"
EXTRAS="bot tools photon"
MODE=""
WITH=()
BUILD=1
MAINTENANCE=1
KEEP_MAINTENANCE=0

usage() {
  cat <<'EOF'
Использование:
  scripts/deploy.sh [--mode monolith|microservices] [--with bot|tools|photon] [--no-build]
                    [--no-maintenance] [--keep-maintenance]
  scripts/deploy.sh maintenance on|off|status
  scripts/deploy.sh status

Развёртывание выбирается глобально: монолит (aef) или микросервисы. Режим берётся из
--mode, иначе из COMPOSE_PROFILES (например, в .env: COMPOSE_PROFILES=monolith).
При смене режима контейнеры другого режима останавливаются и удаляются.

Telegram-бот (профиль bot), kafka-ui (профиль tools) и свой Photon для геокодера (профиль
photon, ему нужен GEO_PHOTON_URL=http://photon:2322 в .env) сами не запускаются. Включить их
можно флагом --with (только вместе с --mode, флаг повторяется) либо в COMPOSE_PROFILES,
например COMPOSE_PROFILES=monolith,bot. Убрать работающий бот: docker compose rm -sf bot.

Деплой: собирает образы (пока работает старая версия), включает режим технических работ,
обновляет контейнеры, дожидается их готовности и снимает режим. Если обновление не удалось,
режим работ остаётся включённым: снять его можно командой "maintenance off".

  --no-build           не собирать образы
  --no-maintenance     не включать режим работ на время обновления
  --keep-maintenance   не снимать режим работ после обновления (снять вручную)

Переменные: WAIT_TIMEOUT (секунды ожидания готовности, 300), SETTLE (пауза на
перечитывание конфигурации Traefik, 3).
EOF
}

log() { printf '==> %s\n' "$*"; }
die() { printf 'Ошибка: %s\n' "$*" >&2; exit 1; }

with_profiles() {
  local profiles="$1"
  shift
  COMPOSE_PROFILES="$profiles" docker compose "$@"
}

services_of() {
  local services
  services=$(COMPOSE_PROFILES="$1" docker compose config --services 2>/dev/null) ||
    { docker compose config -q || true; die "compose-файл не разобран"; }
  printf '%s\n' "$services" | sort
}

detect_mode() {
  local services has_aef=0 has_user=0
  services=$(docker compose config --services 2>/dev/null) ||
    { docker compose config -q || true; die "compose-файл не разобран"; }
  grep -qx aef <<<"$services" && has_aef=1
  grep -qx user <<<"$services" && has_user=1
  if ((has_aef && has_user)); then
    die "включены и монолит, и микросервисы: оставьте один режим (--mode или COMPOSE_PROFILES)"
  elif ((has_aef)); then
    echo monolith
  elif ((has_user)); then
    echo microservices
  else
    die "режим не выбран: укажите --mode или COMPOSE_PROFILES=monolith|microservices"
  fi
}

resolve_mode() {
  local extra profiles
  if [[ -n "$MODE" ]]; then
    [[ " $MODES " == *" $MODE "* ]] || die "неизвестный режим: $MODE (допустимы: $MODES)"
    profiles="$MODE"
    for extra in ${WITH[@]+"${WITH[@]}"}; do
      [[ " $EXTRAS " == *" $extra "* ]] || die "неизвестный профиль: $extra (допустимы: $EXTRAS)"
      profiles+=",$extra"
    done
    export COMPOSE_PROFILES="$profiles"
  else
    ((${#WITH[@]} == 0)) || die "--with работает только вместе с --mode"
    MODE=$(detect_mode)
  fi
  if [[ "$MODE" == monolith ]]; then OTHER=microservices; else OTHER=monolith; fi
}

maintenance_running() {
  [[ -n "$(with_profiles maintenance ps -q --status running maintenance 2>/dev/null)" ]]
}

maintenance_on() {
  log "Включаю режим технических работ"
  with_profiles maintenance up -d --wait --wait-timeout "$WAIT_TIMEOUT" maintenance
  sleep "$SETTLE"
}

maintenance_off() {
  log "Снимаю режим технических работ"
  with_profiles maintenance rm -sf maintenance
  sleep "$SETTLE"
}

stop_other_mode() {
  local others
  mapfile -t others < <(comm -23 <(services_of "$OTHER") <(services_of "$MODE"))
  ((${#others[@]})) || return 0
  if [[ -n "$(with_profiles "$OTHER" ps -aq "${others[@]}")" ]]; then
    log "Останавливаю сервисы режима $OTHER: ${others[*]}"
    with_profiles "$OTHER" rm -sf "${others[@]}"
  fi
}

on_failure() {
  trap - ERR
  if ((MAINTENANCE)) && maintenance_running; then
    printf '\nДеплой не удался. Режим технических работ остаётся ВКЛЮЧЁН.\n' >&2
    printf 'Логи: docker compose logs <сервис>. Снять режим: scripts/deploy.sh maintenance off\n' >&2
  else
    printf '\nДеплой не удался.\n' >&2
  fi
}

summary() {
  if maintenance_running; then log "Режим технических работ: ВКЛЮЧЁН"; else log "Режим технических работ: выключен"; fi
  docker compose ps
}

deploy() {
  resolve_mode
  log "Режим: $MODE"
  if ((BUILD)); then
    log "Собираю образы (старая версия продолжает работать)"
    docker compose build || die "сборка не удалась, ничего не изменено"
  fi
  if ((MAINTENANCE)); then maintenance_on; fi
  trap on_failure ERR
  stop_other_mode
  log "Обновляю контейнеры"
  docker compose up -d --wait --wait-timeout "$WAIT_TIMEOUT"
  if ((MAINTENANCE && !KEEP_MAINTENANCE)); then maintenance_off; fi
  trap - ERR
  summary
}

case "${1:-}" in
  maintenance)
    case "${2:-}" in
      on) maintenance_on ;;
      off) maintenance_off ;;
      status) if maintenance_running; then echo on; else echo off; fi ;;
      *) usage; exit 2 ;;
    esac
    ;;
  status)
    MODE=$(detect_mode || true)
    log "Режим: ${MODE:-не выбран}"
    summary
    ;;
  -h | --help) usage ;;
  *)
    while (($#)); do
      case "$1" in
        --mode) MODE="${2:?--mode требует значение}"; shift 2 ;;
        --with) WITH+=("${2:?--with требует значение}"); shift 2 ;;
        --no-build) BUILD=0; shift ;;
        --no-maintenance) MAINTENANCE=0; shift ;;
        --keep-maintenance) KEEP_MAINTENANCE=1; shift ;;
        -h | --help) usage; exit 0 ;;
        *) usage; die "неизвестный аргумент: $1" ;;
      esac
    done
    deploy
    ;;
esac
