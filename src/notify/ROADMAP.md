# notify — микросервис доставки уведомлений

Сервис отвечает за **управление подписками пользователя на уведомления** и
**оркестрацию доставки** через разные транспорты (transport). Сервис спроектирован
так, чтобы новые способы доставки подключались как плагины, без изменения ядра.

> Статус: `email` (делегируется в `mail`) и `web-push` (доставляется напрямую) —
> реализованы. `telegram`, `mobile`, `realtime` — заложены в архитектуру, но ещё
> не реализованы (см. TODO).

---

## 1. Ключевые принципы

1. **Транспорт-агностичное ядро.** Бизнес-логика (диспетчер) не знает, *как*
   физически доставляется уведомление. Она знает только перечень включённых у
   пользователя транспортов и делегирует доставку объекту-транспорту.
2. **Максимальное делегирование.** Сам `notify` физически доставляет только то,
   что не может делегировать: `web-push`, `mobile`, `realtime`. Всё остальное
   отдаётся профильным микросервисам:
   - `email` → микросервис **`mail`** (SMTP);
   - `telegram` → будущий микросервис **`bot`**;
   - и т.д.
3. **Единый асинхронный API вместо подписок на чужие топики.** `notify` **не**
   подписывается на доменные события каждого сервиса. Вместо этого он
   предоставляет **один входящий топик-API** — `NotifyQueue.SEND`. Любой сервис,
   которому нужно уведомить пользователя, публикует в него `NotificationRequest`.
   Это разворачивает зависимость: домены знают про `notify`, а `notify` не знает
   про домены. Единственное исключение — проекция аккаунтов (см. §4).
4. **Гарантированный транспорт.** `email` всегда включён и не может быть отключён
   пользователем — это запасной канал доставки.
5. **Несколько клиентов на один транспорт.** Под один `(user, transport)` может
   быть зарегистрировано несколько клиентов (например, разные браузеры → разные
   web-push подписки). Это обычная ситуация, а не край.

---

## 2. Доменная модель (БД `notify`)

| Таблица       | Назначение | Источник истины |
|---------------|------------|-----------------|
| `account`     | Проекция аккаунта пользователя (`id → email`, `is_verified`, `locale`). Нужна для резолва адреса гарантированного email-транспорта. | EDA-проекция событий `account.*` сервиса `user`. |
| `preference`  | Переключатели пользователя: какой транспорт включён. `(user_id, transport)` уникально. | Сам `notify` (UI настроек). |
| `client`      | Самостоятельно зарегистрированные точки доставки (web-push подписка, в будущем — device token, chat_id). Транспорт-специфичные данные в JSON-поле `payload`. | Сам `notify` (регистрация с клиента). |

`user_id` хранится как «сырой» UUID без FK на `account` — клиент/настройки могут
появиться раньше, чем долетит проекция аккаунта (eventual consistency), как и в
остальных сервисах проекта.

### Почему email не хранится в `client`
Email-адрес принадлежит сервису `user`. Поэтому email-транспорт резолвит адрес из
проекции `account`, а таблица `client` остаётся только для эндпоинтов, которые
регистрирует сам клиент. Это чисто разделяет «чужие данные» (account) и «свои»
(client).

### Заготовка под категории
`NotificationRequest` несёт поле `category` (`NotificationCategory`). Сейчас
настройки глобальные (per-transport), но когда понадобится матрица
«категория × транспорт», достаточно добавить колонку `category` в `preference`
и поменять резолвер — контракт сообщений уже готов.

---

## 3. Транспорты как плагины

```
transport/
  base.py       BaseTransport (ABC) + DeliveryContext + DeliveryResult
  email.py      EmailTransport(DelegatedTransport)  — публикует в mail
  webpush.py    WebPushTransport(DirectTransport)   — pywebpush + VAPID
  registry.py   реестр: TransportType -> экземпляр
```

`BaseTransport`:
- `type`, `label`, `delegated`, `requires_client`, `is_available()`;
- `validate_client_payload(payload)` — валидация при регистрации клиента;
- `deliver(ctx) -> DeliveryResult`.

Две базовые стратегии:
- **`DelegatedTransport`** — `deliver` публикует сообщение в топик другого
  микросервиса (email → `mail`).
- **`DirectTransport`** — `deliver` сам выполняет протокол доставки (web-push).

**Чтобы добавить новый транспорт:** реализуйте подкласс, зарегистрируйте его в
`registry.py`, добавьте значение в `TransportType`. Ядро и API менять не нужно.

### Контракт делегирования email
Решено: **шаблоны живут в `mail`**. `notify` отправляет
`SendTemplatedEmailRequest{ template, context, recipients, subject }`, а `mail`
рендерит шаблон (Jinja2) и отправляет. Для произвольного уведомления
используется generic-шаблон `templates/email/notification.html`
(`{title, body, action_url}`).

---

## 4. Поток данных

### Входящее уведомление (доставка)
```
domain-service ──publish NotificationRequest──▶ NotifyQueue.SEND
                                                     │
                                          notify: NotificationService.dispatch
                                                     │
                 ┌───────────────────────────────────┼───────────────────────────────┐
                 ▼                                     ▼                               ▼
          load account(email)                 load preferences                load clients(per transport)
                 │                                     │                               │
                 └──────────────► registry.enabled_for(prefs) ◄────────────────────────┘
                                          │
                 ┌────────────────────────┴───────────────────────┐
                 ▼ email (delegated)                               ▼ webpush (direct)
        publish SendTemplatedEmailRequest                  pywebpush → каждому клиенту
              → EmailQueue.SEND (mail)                     мёртвые подписки (404/410) → деактивируются
```

### Синхронизация аккаунта (EDA-проекция)
```
user-service: on_after_register / verify / update / delete
        └─ broker.publish(AccountCreated/Updated/Deleted) → AccountTopic.*
                                   │
                 notify: AccountEventService → upsert/delete в таблице account
```

---

## 5. HTTP API (`/notify/v1`)

| Метод | Путь | Назначение |
|-------|------|------------|
| GET   | `/transports` | Список транспортов + метаданные (label, requires_client, available) для UI. |
| GET   | `/preferences/my` | Текущие настройки пользователя (с дефолтами). |
| PUT   | `/preferences/my` | Сохранить настройки (email принудительно включён, ≥1 транспорт). |
| GET   | `/clients/my` | Клиенты текущего пользователя (например, браузеры). |
| POST  | `/clients/my` | Зарегистрировать клиента (web-push подписка). |
| DELETE| `/clients/my/{id}` | Удалить клиента. |
| GET   | `/webpush/vapid-public-key` | Публичный VAPID-ключ для подписки в браузере. |
| POST  | `/test` | Отправить себе тестовое уведомление (для UI/диагностики). |

---

## 6. Web Push (детали)

- Требуется пара VAPID-ключей. Настройки: `WEB_PUSH_VAPID_PUBLIC_KEY`,
  `WEB_PUSH_VAPID_PRIVATE_KEY` (secret), `WEB_PUSH_VAPID_SUBJECT` (например,
  `mailto:admin@aef`). В проде предпочтительны файловые локаторы
  `WEB_PUSH_VAPID_PUBLIC_KEY_PATH` / `WEB_PUSH_VAPID_PRIVATE_KEY_PATH` (по
  аналогии с RSA-ключами). Если ключи не заданы — транспорт считается
  недоступным (`is_available() == False`), диспетчер его пропускает, endpoint
  ключа отвечает 503.
- Сгенерировать ключи можно так:
  ```bash
  pip install py-vapid
  vapid --gen           # создаст private_key.pem / public_key.pem
  vapid --applicationServerKey   # base64url публичного ключа для фронтенда
  ```
  либо положить PEM в `WEB_PUSH_VAPID_PRIVATE_KEY` (pywebpush принимает и PEM, и
  base64url) или примонтировать файл и указать `WEB_PUSH_VAPID_PRIVATE_KEY_PATH`.
- Фронтенд: service worker `public/sw.js` принимает `push` и показывает
  нотификацию; подписка через `PushManager.subscribe({ applicationServerKey })`.

---

## 7. Масштабирование на новые транспорты — чек-лист

Добавление, например, Telegram:
1. `TransportType.telegram` уже есть → оставить.
2. `transport/telegram.py`: `TelegramTransport(DelegatedTransport)` — публикует в
   топик будущего `bot` (`BotQueue.SEND`).
3. Зарегистрировать в `registry.py`.
4. Клиент регистрирует `chat_id` через `POST /clients/my` (`transport=telegram`,
   `payload={chat_id}`); `validate_client_payload` проверяет наличие `chat_id`.
5. Реализовать сервис `bot`, подписанный на `BotQueue.SEND`.

Mobile / realtime — аналогично, но как `DirectTransport` (FCM/APNs, WS/SSE).

---

## 8. TODO

### Сейчас (MVP)
- [x] Доменная модель: `account`, `preference`, `client`.
- [x] Транспорт-реестр + `EmailTransport` (delegated) + `WebPushTransport` (direct).
- [x] Диспетчер `NotificationService.dispatch` + входящий топик `NotifyQueue.SEND`.
- [x] HTTP API v1 (transports / preferences / clients / vapid / test).
- [x] EDA-проекция `account` ← события `user`.
- [x] `mail`: generic-шаблонный send-handler + `notification.html`.
- [x] Фронтенд: web-push (SW + подписка), панель управления в настройках.
- [ ] **Обновить `uv.lock`** (`uv lock`) после добавления `pywebpush` / `jinja2`
      — Docker-сборки используют `--frozen`.
- [ ] Сгенерировать и прописать VAPID-ключи в `.env` прод/дев окружений.
- [ ] Перегенерировать фронтовый API-клиент (`npm run generate`) после поднятия
      бэкенда — сейчас вызовы notify лежат в рукописном `src/api/notify.ts`.

### Дальше
- [ ] Аудит доставок: таблицы `notification` + `delivery` (статусы, ретраи, DLQ).
- [ ] Ретраи/идемпотентность доставки (dedup по `event_id`).
- [ ] Матрица «категория × транспорт» в `preference`.
- [ ] Транспорты: `telegram` (сервис `bot`), `mobile` (FCM/APNs через Capacitor),
      `realtime` (WS/SSE).
- [ ] Батч-фанаут и троттлинг (rate limiting) на пользователя.
- [ ] Бэкофилл проекции `account` для уже существующих пользователей.
