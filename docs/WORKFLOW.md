# WORKFLOW.md — how to work with CareerPR / Как работать с проектом

Two flows: **A) building the product** (task cards + AI coders) and **B) using the product** (tailoring a CV to a vacancy).
Два флоу: **A) разработка** (карточки + ИИ-кодеры) и **B) использование** (подгонка CV под вакансию).

---
## A. Building: task cards / Разработка по карточкам
EN
1. Open `tasks/README.md`, take the first `todo` card whose dependencies are `done`.
2. Start an AI session (Claude Code / Copilot / Gemini / Cursor). Paste the delegation prompt from `tasks/README.md` + attach exactly ONE card. All instructions are English; the AI answers you in Russian.
3. AI inspects code, reports mismatches, implements the minimum, adds tests, runs `make fmt && make check`.
4. You review the diff (see `DEVELOPMENT.md` §8): scope matches card? golden rules intact? tests present?
5. Squash-merge PR, card → `done`, next card. Never give the AI several cards at once.

RU
1. Откройте `tasks/README.md`, возьмите первую `todo`-карточку с выполненными зависимостями.
2. Запустите сессию ИИ. Вставьте промпт из `tasks/README.md` + приложите ровно ОДНУ карточку. Инструкции на английском, отвечает вам ИИ по-русски.
3. ИИ изучает код, сообщает о расхождениях, делает минимум, пишет тесты, гоняет `make fmt && make check`.
4. Вы смотрите дифф: рамки карточки соблюдены? золотые правила целы? тесты есть?
5. Squash-merge, карточка → `done`, дальше. Несколько карточек за раз ИИ не давать.

Branch/commit: `feat/T-016-validator-v3`, `feat(validators): add V3`. Details: `DEVELOPMENT.md`.

---
## B. Using: from vacancy to PDF / Использование: от вакансии до PDF
```
Fact Base → paste JD → extract reqs → YOU confirm → evidence map + bucket
→ (optional) Stretch suggestions → proposals → validators → YOU approve
→ cover letter → PDF → Gate G4 → immutable snapshot
```
| # | Step (EN) | Шаг (RU) | Who |
|---|---|---|---|
| 1 | Fill Fact Base honestly: roles, dates, tools, metrics, evidence | Заполните Fact Base честно: роли, даты, инструменты, метрики, доказательства | you |
| 2 | Paste vacancy text (URL is best-effort) | Вставьте текст вакансии | you |
| 3 | AI extracts must/nice/hard constraints | ИИ извлекает must/nice/жёсткие ограничения | AI |
| 4 | Confirm/edit requirements (gate G2) | Подтвердите/поправьте требования | you |
| 5 | Evidence map: direct/transferable/potential/genuine_gap + bucket Strong/Possible/Stretch/Blocked (no %) | Карта доказательств + корзина (без %) | system |
| 6 | Stretch: for unmatched low-risk tools AI *suggests* soft wording; you accept / edit / reject each | Stretch: по непокрытым низкорисковым инструментам ИИ *предлагает* мягкую формулировку; вы принимаете/правите/отклоняете | AI → you |
| 7 | Proposals: reorder / pick variant / rewrite; validators V1–V7 check | Предложения: порядок / вариант / переписывание; валидаторы проверяют | AI + code |
| 8 | Review diffs; high-risk and stretch items one by one | Ревью диффов; рискованные и stretch — по одному | you |
| 9 | Cover letter from 2–3 facts + sourced company hook | Письмо из 2–3 фактов + источник о компании | AI |
| 10 | PDF render, page limit, text round-trip, Gate G4 | PDF, лимит страниц, round-trip, гейт G4 | system |
| 11 | Snapshot is frozen; read the **interview-prep list** of stretched items | Snapshot заморожен; прочтите **список для интервью** по stretch-пунктам | you |

### Stretch rules in practice / Stretch на практике
- OK / можно: "Familiar with Terraform (used Ansible/CloudFormation for IaC)", add a tool to Skills, JD terminology, soft level words.
- Never / нельзя: new numbers, dates, employers, titles, degrees, certificates, visa, team size, leadership, "expert".
- Aim: 1–3 stretches per vacancy, not 1:1 match / Цель: 1–3 stretch на вакансию, а не 1:1.
- You own what you claim — be ready to answer about it / Ответственность за заявленное на вас — будьте готовы ответить на интервью.

### Privacy / Приватность
Local-only by default; cloud LLM needs explicit consent. Never commit real CV/JD/PII. / По умолчанию всё локально; облачный LLM — только с согласием. Реальные CV/JD в git не коммитить.
