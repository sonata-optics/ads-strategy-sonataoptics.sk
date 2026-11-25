# Claude Code — отчёт 04d
Автор: Claude Code. 25.11.2026. Задание: [04d_task_to_claude_code.md](04d_task_to_claude_code.md) + [04c_owner_clarifications.md](04c_owner_clarifications.md). **Входной SHA: `f09cbfe`** (часть про каталог — коммит `8df6720`).
Прочитаны: 04c_claude_fix_review.md, все `04c_claude_attachments/`, 04c_chatgpt_decisions.md, пакет 04b. Live Ads/Merchant/сайт **не менялись**; использовались только read-only GAQL-запросы 25.11 (товары, кампании, слоты custom_label). Финансовые данные не выгружались. Финального консенсуса не объявляю.

## Запуск
```bash
python -I discussions/round-04/02_claude_code_attachments/run_all.py
```
Прогоняет весь пакет 02/04b/04d, адаптированные контрпримеры Cowork и сверку каталога 25.11: **67 проверок, все PASS** ([лог](04d_claude_code_attachments/test_run_output_04d.txt)).

| п. 04d | Результат | Файлы |
| --- | --- | --- |
| 1 R4-CLAUDE-09 | Окно подтверждений 6 ч, сброс при hold, тесты W1–W3, C3x, H1, H2 | [stock_sync_dryrun.py](02_claude_code_attachments/stock_sync_dryrun.py), [спец.](02_claude_code_attachments/stock_sync_spec.md) |
| 2 R4-CLAUDE-10 | customer_id 9492722541 обязателен; чужой → ALERT; feed label с дефисом только из разрешённого набора | там же, C2a–C2i |
| 3 R4-CLAUDE-11 | Любой `*_policy_violation` → POLICY_HOLD (35 строк, в т.ч. OOS) | [сверка каталога](04d_claude_code_catalog_refresh.md) |
| 4 R4-CLAUDE-12 | Примеры привязаны к самому слову и реальным товарам 25.11; построчный проект по ответу владельца | [account_negatives_review_v2.csv](04d_claude_code_attachments/account_negatives_review_v2.csv) |
| 5 MONITOR_CV | current/proposed статусы раздельно; R43 → FIXED_LITERAL | [routing_tests_after_proposed_diff.csv](02_claude_code_attachments/routing_tests_after_proposed_diff.csv) |
| 6 R4-CLAUDECODE-07 | Гибридный допуск, пустой генерируемый allowlist, инвентаризация слотов | [план 25.11](04d_claude_code_attachments/full_catalog_coverage_plan_2026-11-25.csv), [слоты](04d_claude_code_attachments/custom_label_inventory_2026-11-25.csv) |
| 7 bresser_role_hint | Категория удалена владельцем; 26916 теперь `monokuláre` (регрессия PASS) | [category_reconciliation.csv](04d_claude_code_attachments/category_reconciliation.csv) |
| 8 Частичный успех | Результат по объекту, `reconcile()` с перечитыванием Ads; тесты P1/P2 | stock_sync_dryrun.py |

## 1–2, 8. Синхронизация наличия v3
- **Окно подтверждений.** `confirmation_window_hours = 6` — проектное значение, равное пределу свежести, а не бизнес-SLA. Старые и будущие подтверждения отбрасываются при каждом подсчёте:
  - W1 — ровно 6 ч, учитывается;
  - W2 — 6 ч 1 мин, отброшено;
  - W3 — дата в будущем, отброшено;
  - C3x — подтверждение 5-дневной давности больше не даёт ENABLE.
- **Hold.** Хранится предыдущее наблюдённое состояние (`hold_seen`). Установка или снятие hold сбрасывает историю: H1 — после снятия нужны два новых чтения; H2 — hold → OOS → unhold → PAUSE. Ограничение: если hold поставили и сняли между двумя опросами, без событий `change_event` этого не видно. Это записано в спецификации.
- **Аккаунт.**
  - У чтения и у каждого управляемого объекта должен быть `customer_id = 9492722541`.
  - Чужой customer (C2c, C2g, C2h), отсутствующий контекст (C2f, C2i) → ALERT, без действий.
  - К короткому ключу customer молча не дописывается.
  - Фикстура C2a исправлена на правильный customer; 1234567890 остался отрицательным тестом.
  - Feed label `SK-2` разбирается и принимается только если он в настроенном наборе (C2d), иначе SKIP (C2e).
- **Частичный успех.**
  - `commit()` принимает результат по каждому объекту; неуспешный не меняет состояние и помечается `needs_reconcile` (P1).
  - `reconcile()` перед циклом доверяет перечитанным статусам и меткам. Пауза человека становится владельцем UNKNOWN и никогда не включается (P2).
  - Изменений API нет.
- Итог: 45/45 сценариев.
  - Адаптированная копия контрпримеров Cowork: 25/25 OK ([скрипт](04d_claude_code_attachments/stock_sync_counterexamples_v2_adapted.py), [вывод](04d_claude_code_attachments/stock_sync_counterexamples_v2_adapted_output.txt)).
  - Оригинал Cowork на v3 даёт 8 PROBLEM ([вывод](04d_claude_code_attachments/stock_sync_counterexamples_v2_original_on_v3_output.txt)). Все 8 — ожидаемый ALERT: в старых фикстурах нет контекста аккаунта.

## 3, 6, 7. Каталог и допуск
См. [04d_claude_code_catalog_refresh.md](04d_claude_code_catalog_refresh.md).
- Свежий снимок 25.11: 7 828 товаров, 4 712 в наличии, 1 720 рекламируются, **2 984 без кампании**.
- `bresser.de` пуста: 384 товара перенесены, 174 нет в Merchant.
- POLICY_HOLD для любого `*_policy_violation` — проверено, в том числе синтетическим новым кодом.
- `not_eligible_in_any_campaign` не считается нарушением политики.
- Генерируемый allowlist пуст, потому что реестра проверок пока нет.
- **Инвентаризация слотов** ([custom_label_inventory](04d_claude_code_attachments/custom_label_inventory_2026-11-25.csv)): **все пять custom_label уже заняты** у всех 7 828 товаров. Свободного слота для `ads_review_ok` нет, поэтому до решения владельца допуск идёт только через генерируемый item_id allowlist. Слоты по номерам:
  - 0 — категория (35 значений);
  - 1 — подкатегория (301 значение, в т.ч. «poľovnícke ďalekohľady» 193);
  - 2 — device/accessory;
  - 3 — ценовой диапазон;
  - 4 — бренд.

  Варианты на решение владельца: перенастроить один слот (например, 3 — ценовой диапазон, если он не используется в кампаниях: НЕТ ДАННЫХ) или оставить allowlist постоянно. Фид не менялся.

## 4. Минус-слова v2 и ответ владельца
[account_negatives_review_v2.csv](04d_claude_code_attachments/account_negatives_review_v2.csv) (258 строк; 04b остаётся историей).
- **Примеры:**
  - Пример из каталога — реальный товар 25.11 (offer_id, название, дата), у которого название буквально совпадает со словом и его match type. Иначе — `NO_VERIFIED_CATALOG_EXAMPLE`.
  - Совпадения только без диакритики показаны отдельно и не называются буквальными.
  - Все запросы помечены «illustrative, not a historical search term»; поисковых запросов E5 нет.
  - Каждый пример проверен тем же движком: слово действительно блокирует свой пример.
- **Две буквальные формы** для каждого слова. `solarna` блокирует «solarna», а «solárna» — нет; товары «solárna nabíjačka» видны только при сравнении без диакритики (4).
  - `ovládanie` — 3 товара в наличии с буквальным совпадением (например, 64768 Celestron SkyPortal WiFi).
  - `kniha` — 2 товара, не в наличии.
  - `free`, `zadarmo`, `drony` — буквального товара в названиях 25.11 нет. У `drony` товары есть, но в названиях стоит «dron».
- **Построчный проект по направлению владельца** (не применён): kde, poradiť, lacno, nie drahé, cheap, popis.
  - `kde`: убрать BROAD; добавить PHRASE для информационных форм («kde je», «kde sa nachádza», «kde pozorovať», «kde vidieť»).
  - Остальные пять: убрать BROAD из списка аккаунта.
  - Это одобрено направлением, а не пакетом: остальные слова (aký, ake, Ktoré, Správny, Nájsť, typy, druhy, stary) остаются OWNER_DECISION. Каталожные 7 — OWNER_DECISION_CATALOG.
- **heureka → OWNER_DECISION_HEUREKA**, два варианта:
  - оставить BROAD — блокирует и навигацию, и «модель + heureka»;
  - заменить на EXACT [heureka], [heureka sk], [heureka.sk] + PHRASE «heureka recenzie», чтобы «модель + heureka» доходил до рекламы.

  Тест второго варианта — только с лимитом расходов владельца; сейчас не разрешён.

## 5. MONITOR_CV
В `routing_tests_after_proposed_diff.csv` два столбца: `current_resolution` и `proposed_resolution_after_A`.
- R18, C09, R43 сейчас MONITOR_CV.
- R43 после варианта A — FIXED_LITERAL (буквальная правка `bazár`); R18/C09 остаются MONITOR_CV.
- Проверки: MONITOR_CV не считается закрытым; NO_CHANGE_NEEDED сейчас → NO_CHANGE_NEEDED после; результат A с риском CV → MONITOR_CV.
- Итог: сейчас 32 без изменений, 10 FIX_PROPOSED, 18 решений владельца, 3 MONITOR_CV, OPEN 0.

## Value — гипотеза владельца
Value тега предположительно «с НДС, без доставки» — **OWNER_REPORTED_UNVERIFIED**. Канонические формулы (без НДС и доставки) не менялись, коэффициент 1.23 не применяется.
План технической сверки, без заказов и изменений тега:
1. Конфигурация действия-конверсии в Ads (источник, value, count).
2. Связь с GA4 и импорт: нет ли двойного учёта.
3. Одно обезличенное событие purchase: items после скидок, tax, shipping, currency, transaction_id.
4. Сравнение с заказом в CS-Cart и фактически переданным value.

Результат — отдельная запись, без персональных данных.

## Открыто
- Реестра `ads_review_ok` нет; свободного custom_label нет — нужно решение владельца.
- E4/E5/E8, маржи, лимит расходов L; источник value.
- Причины исчезновения 1 781 ID (сверка с CS-Cart).
- Пилот: 3 ID отсутствуют (26131, 47424, 47458), состав пересобрать перед созданием.
- Hold между опросами — только через change_event.
- Ни одна политика или минус-слово в кабинете не менялись.

## Передача — Claude Cowork (04e, коротко)
Ответ: `discussions/round-04/04e_claude_review.md`, затем ChatGPT. Live запрещено.
1. Запустить `run_all.py`; проверить W1–W3, C3x, H1/H2, C2a–C2i, P1/P2 и адаптацию своих контрпримеров (сравнить с оригиналом: 8 PROBLEM только из-за отсутствия контекста аккаунта).
2. Сверка каталога 25.11: суммы, миграция `bresser.de` по ID, POLICY_HOLD для всех `*_policy_violation`, пустой allowlist, отсутствие свободного custom_label.
3. `account_negatives_review_v2.csv`: соответствие примеров слову и match type, честность NO_VERIFIED_CATALOG_EXAMPLE, построчный проект по ответу владельца, heureka.
4. MONITOR_CV: current/proposed, R43.

По каждому пункту: принято / оспорено / непроверено.
