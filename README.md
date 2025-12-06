Проект включает:
- Keycloak (SSO, OAuth2, PKCE)
- Frontend (React)
- Backend API для отчётов (Java, Spring Boot)
- ETL процесс (Apache Airflow)
- OLAP БД (ClickHouse)
- Источники данных (PostgreSQL)

---

## Архитектура (кратко)

- **Протезы** → телеметрия
- **CRM (PostgreSQL)** → данные пользователей
- **Apache Airflow** → ETL, агрегация, подготовка витрин
- **ClickHouse** → хранение готовых агрегированных отчётов
- **Reports API (Spring Boot)** → `/reports`
- **Frontend (React)** → UI + загрузка отчёта
- **Keycloak** → аутентификация и авторизация пользователей

---

## Требования

- Docker
- Docker Compose
- Git

---

## Запуск проекта

### 1. Клонировать репозиторий

git clone <repository-url>

cd architecture-bionicpro

---

### 2. Запуск всех сервисов

Из корня проекта:
`
docker compose up -d --build
`
## Доступ к интерфейсам

### Frontend
http://localhost:3000

После логина отображается страница **Usage Reports** с кнопкой **Download Report**.

---

### Keycloak (Admin Console)
http://localhost:8080

* Username: `admin`
* Password: `admin`

Realm: `reports-realm`

---

### Airflow UI
http://localhost:8081

* Username: `admin`
* Password: `admin`

DAG: `bionicpro_reports_daily`

---

## Пользовательский сценарий

1. Пользователь открывает Frontend (`localhost:3000`)
2. Происходит редирект в Keycloak
3. После успешного логина пользователь возвращается в приложение
4. Нажатие **Download Report**:

   * Frontend отправляет запрос `GET /reports`
   * Reports API извлекает данные из ClickHouse
   * Пользователю возвращается CSV-файл отчёта

---

## ETL / Airflow

* DAG расположен в:

  
  airflow/dags/bionicpro_reports_daily.py
 

* Выполняется по расписанию:

  
  каждый день в 02:00
 

* Этапы:

  1. Extract — CRM (PostgreSQL)
  2. Extract — телеметрия
  3. Transform — агрегация по пользователям
  4. Load — витрина в ClickHouse

Отчётный backend читает **готовую витрину** без тяжёлых вычислений.

---

## Reports API

### Endpoint
GET /reports

Особенности:

* Требует Bearer Token (OAuth2)
* Срабатывает только для аутентифицированного пользователя
* Пользователь может получить **только свой отчёт**
* Данные берутся из ClickHouse

Формат ответа:

* CSV-файл для скачивания

---

## Остановка проекта
bash
docker compose down

(данные в volumes сохраняются)

---
