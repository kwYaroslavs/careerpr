# Task cards — execution order / Порядок выполнения задач

> EN: Cards are written in English so any AI can read them; each has a Russian block for you. One card = one AI session = one branch = one PR. Take the first `todo` card whose dependencies are `done`.
> RU: Карточки на английском (для ИИ) + русский блок (для вас). Одна карточка = одна сессия ИИ = одна ветка = один PR. Берите первую `todo`, у которой все зависимости `done`.

Statuses / Статусы: `todo` · `doing` · `review` · `done`.

| ID | Title / Название | Milestone | Depends | Status |
|---|---|---|---|---|
| T-001 | Scaffold and quality gates<br><sub>Каркас проекта и проверки качества</sub> | M0 | — | done |
| T-002 | Core domain contracts<br><sub>Базовые доменные контракты</sub> | M0 | T-001 | done |
| T-003 | Database models and migration baseline<br><sub>Модели БД и базовая миграция</sub> | M0 | T-002 | done |
| T-004 | Gateway protocol and FakeLLM<br><sub>Протокол Gateway и FakeLLM</sub> | M0 | T-002 | todo |
| T-005 | Prompt loader and LLM run logging<br><sub>Загрузчик промптов и логирование LLM-запусков</sub> | M0 | T-003,T-004 | todo |
| T-006 | Fact Base write/read services<br><sub>Сервисы записи/чтения Fact Base</sub> | M0 | T-003 | todo |
| T-007 | Structured Master Resume and Base Resume<br><sub>Структурированные Master и Base Resume</sub> | M0 | T-002,T-006 | todo |
| T-008 | Job description intake<br><sub>Приём текста вакансии</sub> | M1 | T-003 | todo |
| T-009 | Requirement extraction contract and prompt<br><sub>Контракт и промпт извлечения требований</sub> | M1 | T-004,T-008 | todo |
| T-010 | Requirement confirmation API<br><sub>API подтверждения требований</sub> | M1 | T-009 | todo |
| T-011 | Skill normalization and reviewed aliases<br><sub>Нормализация навыков и проверенные алиасы</sub> | M1 | T-002 | todo |
| T-012 | Requirement-to-fact evidence map<br><sub>Карта «требование → факт»</sub> | M1 | T-006,T-010,T-011 | todo |
| T-013 | Hard-constraint gate and fit bucket<br><sub>Гейт жёстких ограничений и корзина соответствия</sub> | M1 | T-012 | todo |
| T-014 | Validator V1 and proposal reference checks<br><sub>Валидатор V1 и проверка ссылок предложений</sub> | M1 | T-002,T-007,T-012 | todo |
| T-015 | Validator V2 number/date protection<br><sub>Валидатор V2: защита чисел и дат</sub> | M1 | T-006,T-014 | todo |
| T-016 | Validator V3 fact-backed entity and claim protection<br><sub>Валидатор V3: защита сущностей и утверждений</sub> | M1 | T-006,T-011,T-014 | todo |
| T-017 | Validators V5–V7 and unified validation result<br><sub>Валидаторы V5–V7 и единый результат валидации</sub> | M1 | T-014 | todo |
| T-018 | R0/R1 deterministic proposal generation<br><sub>Детерминированная генерация предложений R0/R1</sub> | M1 | T-010,T-012,T-013 | todo |
| T-019 | R2 rewrite contract and prompt<br><sub>Контракт и промпт переписывания R2</sub> | M1 | T-004,T-016,T-017,T-018 | todo |
| T-020 | Proposal validation, lifecycle and idempotency<br><sub>Валидация, жизненный цикл и идемпотентность предложений</sub> | M1 | T-003,T-017,T-018,T-019 | todo |
| T-021 | Cover letter generation<br><sub>Генерация сопроводительного письма</sub> | M1 | T-017,T-019,T-020 | todo |
| T-022 | Markdown renderer<br><sub>Рендерер Markdown</sub> | M1 | T-007,T-020,T-021 | todo |
| T-023 | PDF renderer and fit-loop<br><sub>PDF-рендерер и fit-loop</sub> | M1 | T-022 | todo |
| T-024 | Readiness Gate G4 and immutable snapshot<br><sub>Гейт готовности G4 и неизменяемый snapshot</sub> | M1 | T-020,T-021,T-023 | todo |
| T-025 | Golden end-to-end and adversarial suite<br><sub>Golden e2e и состязательные тесты</sub> | M1 | T-008,T-009,T-013,T-020,T-021,T-024 | todo |
| T-026 | Real LLM provider behind Gateway<br><sub>Реальный LLM-провайдер за Gateway</sub> | M2 | T-025 | todo |
| T-027 | Frontend profile and Fact Base screens<br><sub>Фронтенд: профиль и Fact Base</sub> | M2 | T-006,T-007,T-025 | todo |
| T-028 | Frontend vacancy and proposal review workspace<br><sub>Фронтенд: вакансия и ревью предложений</sub> | M2 | T-010,T-012,T-020,T-021,T-025,T-027 | todo |
| T-029 | MVP-0 acceptance on real vacancies<br><sub>Приёмка MVP-0 на реальных вакансиях</sub> | M3 | T-026,T-028,T-030 | todo |
| T-030 | Stretch layer: user-approved claim softening<br><sub>Слой Stretch: приукрашивание с одобрением пользователя</sub> | M1 | T-006,T-016,T-020 | todo |
| T-031 | Career adaptation contracts<br><sub>Контракты адаптации карьеры</sub> | M0 | T-002 | review |
| T-032 | Skill Graph and Role Taxonomy storage<br><sub>Хранилище Skill Graph и Role Taxonomy</sub> | MVP-1 | T-011,T-031 | todo |
| T-033 | Transferable Skills Discovery<br><sub>Поиск переносимых навыков</sub> | MVP-1 | T-004,T-016,T-032 | todo |
| T-034 | Gap analysis<br><sub>Анализ пробелов</sub> | MVP-1 | T-012,T-033 | todo |
| T-035 | Role Discovery and search modes<br><sub>Поиск ролей и режимы поиска</sub> | MVP-1 | T-032,T-033 | todo |
| T-036 | Adaptive Tailoring for distant roles (V10)<br><sub>Адаптация резюме под далёкие роли (V10)</sub> | MVP-1 | T-019,T-020,T-033 | todo |
| T-037 | Frontend: modes, role directions, match categories<br><sub>Фронтенд: режимы, направления, категории</sub> | MVP-1 | T-028,T-035,T-036 | todo |

## How to delegate to an AI / Как отдать задачу ИИ
Copy this prompt and attach exactly one card / Скопируйте промпт и приложите ровно одну карточку:

> Read `AGENTS.md`, `docs/DEVELOPMENT.md`, and the single task card I provide. Implement only that card. Do not implement future cards, refactor unrelated files, invent fields/endpoints, or change architecture. First inspect the current code and report any mismatch with the card. Then implement the smallest complete change, add tests, run `make fmt` and `make check`, inspect `git diff`, update the task status/index, and summarize changed files, test results, and open questions. If the card conflicts with code or docs, stop and explain; do not silently expand scope. Write all code, comments, commit messages and docs in English; answer me in Russian.

Full step-by-step flow / Полный флоу: `docs/WORKFLOW.md`.

## Dependency rule / Правило зависимостей
EN: Do not start a card until all dependencies are merged and `done`. Split a card if it exceeds ~400 changed lines.
RU: Не начинать карточку, пока зависимости не влиты и не `done`. Если карточка больше ~400 строк диффа — сначала разбить.
