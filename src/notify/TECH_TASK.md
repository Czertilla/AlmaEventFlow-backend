# Техническое задание на разработку MVP микросервиса notify

## 1. Назначение микросервиса

Микросервис `notify` предназначен для централизованной оркестрации персональной доставки уведомлений пользователям системы.

В рамках MVP микросервис должен поддерживать два персональных транспорта доставки:

1. `email`;
2. `web_push`.

Архитектура MVP должна быть спроектирована так, чтобы в дальнейшем без полной переработки модели и API можно было добавить:

1. `mobile_push`;
2. `telegram_private`;
3. `realtime`;
4. `in_app inbox`;
5. дополнительные transport worker’ы;
6. расширенные пользовательские настройки уведомлений.

Микросервис `notify` не должен самостоятельно выполнять отправку email и по возможности не должен напрямую взаимодействовать с внешними провайдерами доставки, если для этого существуют специализированные сервисы.

Микросервис `notify` не отвечает за публикацию сообщений в общие чаты коллективов, каналы, группы или внешние публичные площадки. Такие публикации должны реализовываться отдельным announcement/integration pipeline через EDA-топики и специализированные bot/social-сервисы.

## 2. Границы ответственности

### 2.1. Notify отвечает за

`notify` должен отвечать за:

1. хранение локальной проекции аккаунтов пользователей;
2. хранение пользовательских настроек доставки;
3. хранение персональных endpoint’ов доставки;
4. приём запросов на персональные уведомления;
5. идемпотентную обработку notification request;
6. массовую фильтрацию пользователей по настройкам доставки;
7. создание delivery-задач по каналам;
8. постановку delivery-задач в outbox;
9. публикацию задач в Kafka;
10. маршрутизацию задач в специализированные сервисы доставки;
11. хранение статусов доставки;
12. обработку временных и постоянных ошибок доставки;
13. деактивацию невалидных endpoint’ов;
14. сохранение базы для последующего добавления Telegram, mobile push и realtime.

### 2.2. Notify не отвечает за

`notify` не должен отвечать за:

1. вычисление состава участников мероприятия;
2. хранение бизнес-логики мероприятий, коллективов и attendance;
3. публикацию сообщений в общие Telegram-чаты коллективов;
4. хранение Telegram group chat_id;
5. хранение прав Telegram-бота в чатах;
6. управление привязкой коллективов к внешним чатам;
7. синхронную гарантию, что все пользователи получили уведомление;
8. показ уведомления в клиентском интерфейсе;
9. авторизацию пользователей в основном приложении;
10. непосредственную отправку email через SMTP или внешние email provider'ы.

## 3. Основной сценарий использования

### 3.1. Сценарий: создание мероприятия/участия

1. Руководитель коллектива создаёт мероприятие или участие в мероприятии.
2. Доменный сервис мероприятий создаёт 30+ `attendance` со статусом `active`.
3. Доменный сервис мероприятий формирует список `user_id`, которых нужно уведомить персонально.
4. Доменный сервис публикует Kafka-сообщение в топик персональных уведомлений.
5. `notify` получает notification request.
6. `notify` проверяет идемпотентность запроса.
7. `notify` создаёт логическое уведомление.
8. `notify` массово получает настройки доставки пользователей.
9. `notify` массово получает endpoint’ы пользователей.
10. `notify` применяет бизнес-правила выбора каналов.
11. `notify` создаёт delivery-задачи для `email` и `web_push`.
12. `notify` публикует delivery-задачи через transactional outbox.
13. `mail-service` отправляет email.
14. Web push worker отправляет web push-уведомления.
15. Результаты доставки сохраняются в БД.

## 4. Архитектурное решение

### 4.1. Общая схема

```text
event-service
    |
    | Kafka: notifications.personal.requested
    v
notify-api / notify-consumer
    |
    | PostgreSQL transaction
    | - notification
    | - notification_recipients
    | - notification_deliveries
    | - outbox_events
    v
outbox-publisher
    |
    | Kafka
    | - notify.delivery.email
    | - notify.delivery.web_push
    v
specialized services
    |
    | external providers
    | - mail-service
    | - Web Push provider
```

### 4.2. Внутренние компоненты

MVP должен включать следующие компоненты:

1. `notify-api`;
2. `notification-request-consumer`;
3. `outbox-publisher`;
4. `web-push-worker`;
5. `account-projection-consumer`.

Email worker внутри `notify` не требуется.

Опционально допускается объединить `notify-api` и `notification-request-consumer` в одном приложении, но логически они должны быть разделены.

## 5. Транспорты доставки

### 5.1. Поддерживаемые в MVP

```text
email
web_push
```

### 5.2. Зарезервированные на будущее

```text
mobile_push
telegram_private
realtime
in_app
```

### 5.3. Важное разграничение

`telegram_private` в будущем должен использоваться только для персональной доставки пользователю.

Публикация в общий чат коллектива не должна проходить через персональный `notify` pipeline. Для неё должен использоваться отдельный топик вида:

```text
announcements.collective.requested
```

Подписчиком на этот топик должен быть Telegram bot service или другой integration service.

### 5.4. Принцип специализированных сервисов

По возможности непосредственной отправкой уведомлений должны заниматься специализированные сервисы.

Примеры:

* `email` → `mail-service`;
* `telegram_private` → `telegram-bot-service`;
* `mobile_push` → `push-service`.

Исключениями являются transport'ы, тесно связанные с самим `notify`, например:

* `web_push`;
* `in_app`;
* `realtime`.

`notify` выступает координатором и владельцем бизнес-логики уведомлений, а не универсальным сервисом отправки.

## 18. Kafka-топики

### 18.1. Входящие топики

```text
account.created
account.updated
account.email_verified
notifications.personal.requested
```

### 18.2. Внутренние delivery-топики

```text
notify.delivery.email
notify.delivery.web_push
```

### 18.3. Подписчики

```text
notify.delivery.email -> mail-service
notify.delivery.web_push -> web-push-worker
```

### 18.4. Зарезервированные будущие топики

```text
notify.delivery.mobile_push
notify.delivery.telegram_private
notify.delivery.realtime
```

### 18.5. Dead-letter топики

```text
notify.delivery.email.dlq
notify.delivery.web_push.dlq
notifications.personal.requested.dlq
```

## 22. Email delivery

Отправка email не должна выполняться внутри `notify`.

`mail-service` должен:

1. читать сообщения из `notify.delivery.email`;
2. загружать delivery по API или через собственную проекцию;
3. проверять финальный статус;
4. проверять `notification.expires_at`;
5. загружать account пользователя;
6. проверять `account.email`;
7. проверять `account.is_verified`;
8. рендерить шаблон или использовать готовый content;
9. отправлять email через provider;
10. сохранять результат provider’а;
11. переводить delivery в `sent` или `failed`;
12. при временной ошибке назначать retry.

Для MVP допускается SMTP provider.

Интерфейс provider должен быть абстрактным, чтобы в будущем заменить SMTP на SendGrid, Mailgun, Amazon SES или другой API provider.

## 23. Web Push worker

Web Push worker должен:

1. читать сообщения из `notify.delivery.web_push`;
2. загружать delivery из БД;
3. блокировать delivery на время изменения статуса;
4. проверять финальный статус;
5. проверять `notification.expires_at`;
6. загружать recipient_endpoint;
7. проверять `endpoint.status = active`;
8. рендерить web push payload;
9. отправлять push через Web Push provider;
10. сохранять результат;
11. при постоянной ошибке помечать endpoint как `invalid`;
12. при временной ошибке назначать retry.

Web push является допустимым исключением, так как тесно связан с моделью endpoint'ов внутри `notify`.

## 30. Конфигурация

MVP должен поддерживать переменные окружения:

```text
DATABASE_URL

KAFKA_BOOTSTRAP_SERVERS
KAFKA_CONSUMER_GROUP
KAFKA_SECURITY_PROTOCOL

WEB_PUSH_VAPID_PUBLIC_KEY
WEB_PUSH_VAPID_PRIVATE_KEY
WEB_PUSH_VAPID_SUBJECT

NOTIFY_DEFAULT_LOCALE
NOTIFY_DEFAULT_TIMEZONE

OUTBOX_BATCH_SIZE
OUTBOX_POLL_INTERVAL_SECONDS

DELIVERY_MAX_ATTEMPTS
```

SMTP-конфигурация должна находиться в `mail-service`.

## 33. Критерии готовности MVP

MVP считается готовым, если:

1. Микросервис принимает notification request через Kafka.
2. Микросервис поддерживает локальную проекцию account.
3. Микросервис хранит preferences пользователя.
4. Микросервис запрещает отключение всех способов доставки.
5. Email включён по умолчанию.
6. Микросервис умеет регистрировать web push endpoint.
7. Микросервис создаёт notification и delivery-задачи идемпотентно.
8. Email доставляется через отдельный `mail-service`.
9. Микросервис отправляет web push.
10. Delivery-задачи публикуются через transactional outbox.
11. Workers и специализированные сервисы поддерживают retry и permanent failure.
12. Невалидные web push endpoint’ы деактивируются.
13. Кодовая архитектура позволяет добавить `mobile_push`, `telegram_private`, `realtime` без переписывания notification request pipeline.
14. Общие чаты коллективов не реализованы внутри notify и остаются зоной ответственности отдельного announcement/integration pipeline.
15. Архитектура ориентирована на делегирование непосредственной доставки специализированным сервисам.
