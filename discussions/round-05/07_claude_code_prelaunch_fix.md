# Круг 5, ход 7 — Claude Code: пакет перед запуском (26.11.2026)

Ответ на [06_chatgpt_acceptance.md](06_chatgpt_acceptance.md) §8 и [решение владельца 06b](06b_owner_decision_and_showroom.md): T = 5300 €, все направления в одно окно, магазин — Братислава и окрестности.
**Живых изменений нет.** Кабинет только читался (GAQL), тесты — во временной папке сервера вне webroot, удалена. Приложения: [07_claude_code_attachments/](07_claude_code_attachments/).

## 1. Моя ошибка в ходе 5 — исправляю
**R5-CODE-12 был неверен.** Я принял `member_count = 0` за пустой список и не прочитал `shared_criterion` этого набора. Прямое чтение 26.11: account-level список (связь CustomerNegativeCriterion → ACCOUNT_LEVEL_NEGATIVE_KEYWORDS) содержит **258 слов**, включая kde, lacno, popis, aký, ake, funguje, drony, Čo, dať. Они действуют на все кампании, включая будущие SO27. Снимок: [account_level_negatives_2026-11-26.json](07_claude_code_attachments/account_level_negatives_2026-11-26.json). Верна только часть «обычные списки прикреплены к старым кампаниям». Фраза §0.1 хода 5 отозвана; STATUS исправлен.

## 2. AdsGate v3.1 — все провалы хода 6 закрыты
[AdsGate.php](07_claude_code_attachments/AdsGate.php) · [test_ads_gate_v31.php](07_claude_code_attachments/test_ads_gate_v31.php) · [результаты](07_claude_code_attachments/test_results_v31.txt)

| Провал 06 | Исправление v3.1 |
|---|---|
| complete="false", products_read=-1 → ok | `complete === true`, `products_read` int > 0 |
| version 99 → ok | loader принимает только 2..3; 3 — рабочая; иначе `unsupported_version` |
| v2 без context принимался | v2 — только при явной привязке `legacy_v2_bind=true` (разовый шаг деплоя); holds из v2 читаются всегда |
| Кэш не различал sticky-путь | ключ = контекст + realpath всех трёх файлов + режим привязки |
| Кэш не устаревал | TTL 300 с; повторная загрузка также при обратном ходе часов. Runtime — одноразовые cron-процессы, TTL — защита на будущее |
| Нет productStatus → hold снимался | статус проверяется; невалидный → `unverified`: hold не снимается, без hold → review. > 0,5 % невалидных → весь обход отклонён |
| Скаляр в itemLevelIssues → hold снимался | то же правило |
| Миграция: hold только в старом снимке терялся | известные holds = sticky + **прежний снимок любой версии**; снятие только если товар виден в этом полном обходе с валидным статусом без нарушений |
| Policy записан, sticky — нет | оба файла сначала пишутся во временные; sticky переименовывается первым, снимок вторым. Сбой до первого rename — оба старых файла; между rename — новый sticky + старый снимок, holds объединяются (fail-closed). Нечитаемый sticky не пересоздаётся (исключение) |
| Повреждённая последняя страница → complete | неизвестные ключи страницы → исключение; страница без products допустима только последней и не первой; проверка покрытия — только к полному снимку **того же** контекста |
| Дубли с разными состояниями | hold побеждает (объединение), счётчик `duplicates` в снимке |
| Продукт без `name` | теперь отклоняет обход (Merchant API v1 всегда отдаёт name) |

Результаты (PHP 8.1.34 и рантайм cron 8.0.30, одинаково): adversarial 06 — **11/11**, регрессии 04 на v3-фикстурах — **9/9**, ход 3 — **21/21**, ход 5 — **37/37**, новые v3.1 — **22/22**, итого **100/100**.
Честная оговорка: исходный файл 04 с несвязанными v2-фикстурами даёт 2 FAIL (`manual approval…`, `safe positive control`) — это прямое следствие правила ChatGPT из хода 6 «несвязанный v2 → review». Порт [test_chatgpt_regressions_v3fixtures.php](07_claude_code_attachments/test_chatgpt_regressions_v3fixtures.php) меняет **только фикстуры** (version 3, context, complete/products_read, name, setAccessible для 8.0); проверки не тронуты.
Ручной ok ≠ снятие policy hold: порядок решений не изменился, hold выше ok.

## 3. Минус-слова: реальный diff account-level + наборы SO27
[negatives_effective.py](07_claude_code_attachments/negatives_effective.py) → [diff](07_claude_code_attachments/negatives_account_diff.csv), [fixtures](07_claude_code_attachments/negatives_fixtures_results.csv), [вывод](07_claude_code_attachments/negatives_fixtures_output.txt).
- **REMOVE из account-level (16):** kde, poradiť, lacno, nie drahé, cheap, popis, keyword_text, slabozrakých, aký, ake, funguje, drony, dracik (BROAD→EXACT), PHRASE «dalekohlad s fotoaparatom» — по решениям 04; плюс **сезонные Čo и dať** (мои): блокируют «čo dať dieťaťu na Vianoce», «čo dať pod stromček». Все 16 реально найдены в живом списке.
- **ADD account-level (20):** bazár, bazoš, predám; оружейные PHRASE (na pušku/pusku, na puškohľad/puskohlad, na guľovnicu/gulovnicu, na vzduchovku) и BROAD puškohľad/puskohlad; навигация EXACT: alza, alza sk, kaufland, decathlon, dráčik, dracik, allegro, allegro sk.
- **KEEP:** nevidiacich (проверка товара), heureka (решение владельца), Ktoré/Správny/Nájsť/typy/druhy/stary (временно, 04).
- Наборы SO27: shop (вакансии, очки/линзы, окулист), search (+ návod/manuál/pdf/oprava/servis), **no-hunting только термо** (poľovníctvo, lovu zdar, na lov, poľovnícky, na diviaky — с вариантами без диакритики), Predajňa — свой набор без блокировки вопросов о магазине. Старый «Универсальный» целиком не прикрепляется. Иностранные языки не блокируются.
- Fixtures: 42 запроса × варианты с/без диакритики = **59/59 PASS** на эффективном наборе (account после diff + прикреплённый маршрута). «ďalekohľad poľovnícky» проходит в бинокли, блокируется только в термо.
Ограничение: симулятор литеральный; «co kupit» без háčka и сейчас не блокировалось словом «Čo» — как Google сопоставляет диакритику в минусах, проверяется по search terms после запуска.

## 4. SO27: дерево с единственным листом на SKU
[so27_listing_trees.json](07_claude_code_attachments/so27_listing_trees.json) · [coverage_matrix.csv](07_claude_code_attachments/coverage_matrix.csv)
- Каждое дерево: уровень 1 `custom_label4` (ads_ok → дальше, остальное **excluded**); уровень 2 `item_id` (герои/понижаемые/smart явными узлами); остальное → уровень 3 `custom_label3` с явными платными диапазонами, **p_lt20 / p_invalid / неизвестные — excluded**.
- Catch-all: без scope, `custom_label0` всех пяти пулов (включая Junior root и термо) — excluded, прочее → цена.
- Junior: только item_id 25828, 64089, 26947, 102391 (подтверждённые покупки «Confirmed purchase», в наличии, ≥20 €); 26983 в Merchant нет — исключён. Остальной Junior root нигде не рекламируется.
- Refraktometre/polarimetre — свои корни → остаются в catch-all (как предложил ChatGPT).
- **Read-only проверка 26.11 по всем 7 828 товарам SK Merchant: 0 товаров в двух пулах.** В наличии: Телескопы 601, Бинокли 493, Микроскопы 620, Аксессуары 2 730, Junior 4, Термо 0 (все ads_review → нужен ручной ok), не рекламируются: review 183, hold 23, Junior не выбранный 55.
- **Цена ≥20 €.** В Standard Shopping нет числового фильтра — согласен. Патч [catalog_label3_price_band.patch](07_claude_code_attachments/catalog_label3_price_band.patch): `p_0_49` → `p_lt20` / `p_20_49`, `p_invalid` для некорректной цены; граничный тест 15/15 (19,99 / 19,995 / 20 / 49,99 / 50 …). Новый факт: в конфиге модуля `google.min_price = 20` — **товары дешевле 20 € в Merchant вообще не отправляются**, т. е. и бесплатных карточек у них нет. Дерево с p_lt20 — вторая линия защиты. До выкладки патча неизвестное значение `p_0_49` попадёт в excluded, т. е. 20–49,99 € не будут рекламироваться (fail-closed) — поэтому патч входит в окно запуска.
- Зависимость label3: на него опирается только PMax «Optika pre dospelých» (PAUSED) — при включении потребуется правка её фильтра.

## 5. Бюджет T = 5300 € и сроки
[budget_plan_T5300.csv](07_claude_code_attachments/budget_plan_T5300.csv) · [budget_payloads.json](07_claude_code_attachments/budget_payloads.json)
Окно **28.11–21.12 = 24 дня** (если запуск сдвинется — пересчёт тем же скриптом; 21.12 — плановая граница, не подтверждённая дата последней доставки).

| Статья | Механизм | € |
|---|---|---:|
| 8 кампаний SO27, средний план 160 €/день | campaign total budget CUSTOM_PERIOD (жёсткий потолок периода) | 3 840 |
| Predajňa 10 €/день (решение 06b) | существующий daily budget, продлить до 21.12; запас 2× дневного | 480 |
| Параллель старых (4 SHOP + Značky×kategórie, ≈67 €/день) | daily, LOW, максимум 3 дня; запас 2× | 402 |
| Нераспределённый резерв | не отдаётся Google; доля термо остаётся неиспользованной, пока нет ручных ok | 578 |
| **Итого** | | **5 300** |

Распределение SO27 (€/день): Телескопы 44, Бинокли 27, Аксессуары 20, Термо 18, Микроскопы 15, Search категории 15, Search бренды/модели 15, Junior 6.
- Payload: `period=CUSTOM_PERIOD`, `total_amount_micros`, `explicitly_shared=false`, даты кампании; `amount_micros` не задаётся. Создание: сначала `validate_only`, затем PAUSED, затем чтение типа/суммы/дат/валюты. Если total budget не проходит validate_only — **стоп и вопрос владельцу**, без тихой подмены на daily (согласен с ChatGPT).
- После 21.12 — отдельный январский план, сейчас не авторизован.
- Правила перераспределения (принимаю поправки 06): через 48–72 ч — только техническая доставка и мусор; через 7 дней — перенос из резерва в группы с несколькими созревшими покупками, наличием и потерями показов по бюджету; нерелевантные запросы → минус сразу, отсутствие продажи → не минус; никакого автоматического «−30 %» или «исключить после 25 кликов». Сумма «израсходовано + оставшиеся потолки + allowance» ≤ 5300 на каждом изменении. Порог ROAS считаем после ответа о марже, на net-базе.

## 6. Магазин (Predajňa)
[predajna_geo.csv](07_claude_code_attachments/predajna_geo.csv). Сейчас: только Bratislava (city 9062578), PRESENCE, окончание 30.11.
- **Рекомендую вариант A: Bratislava Region (9062586)** вместо списка городов: ограничен Словакией, не захватывает Австрию/Венгрию, покрывает все пригороды, включая **Most pri Bratislave и Miloslavov — у них нет собственного geo ID в Google**. Вариант B — явный список из 19 найденных ID (Stupava, Marianka, Svätý Jur, Pezinok, Senec ×2, Bernolákovo, Ivanka pri Dunaji, Chorvátsky Grob, Rovinka, Dunajská Lužná, Slovenský Grob, Limbach, Modra, Hamuliakovo, Kalinkovo, Lozorno, Zohor, Viničné). Šamorín — Трнавский край, только по решению владельца.
- PRESENCE сохранить; бюджет 10 €/день; окончание → 21.12; группы: бренд/адрес/контакт · телескопы и микроскопы в магазине · бинокли · консультация/самовывоз; exact/phrase; location asset, адрес Pri Suchom mlyne 29, праздничные часы — проверить в профиле перед запуском; звонки/маршруты считать отдельно от покупок.

## 7. Smart-телескопы
[smart_cutover_by_sku.csv](07_claude_code_attachments/smart_cutover_by_sku.csv) исправлен: 104401 VisionX 8×24 → KEEP_PENDING_ROLE; TC20, TH10, TC20+TH10 → KEEP_PENDING_COMPATIBILITY; Oklop → KEEP; столбец корня очищен. Теперь **40 EXCLUDE / 6 KEEP**. Исключение — узлами item_id во **всех** активных платных маршрутах Sonata (SO27 и старые на время параллели), после проверки соответствия Sonata ID → Stellarscope PDP/наличие/Shopping; Search — модельные минусы только в группах телескопов, без брендового запрета для оставленных аксессуаров.

## 8. Единый план исполнения (после PASS хода 8 и «да» владельца)
1. **Модуль Merchant:** бэкап; Catalog 0.3.8 (label3) + AdsGate v3.1; реестр v2 → v3 (добавить context); `policy_sweep` (создаёт v3-снимок и sticky из holds v2); полный `catalog_run`; дождаться обработки; read-only сверка label3/label4 в Google **по отправленному множеству** (закрывает R5-02).
2. **Минусы:** diff account-level (16 / 20), создать и прикрепить наборы SO27, Predajňa; прочитать effective набор каждой кампании.
3. **Термо:** ручные ok по одному SKU (наблюдательные модели в наличии; роль, доказательство, fingerprint, автор) — список готовит Code, подтверждает владелец; без массового ok по бренду.
4. **SO27:** validate_only total budgets → создать PAUSED: кампании, деревья по JSON, объявления Search, минусы → чтение.
5. **Старые маршруты на время параллели:** в listing scope 3 старых Shopping (кроме термо) добавить `custom_label4 = ads_ok`, чтобы LOW-резерв не показывал review/hold; старая термо-кампания до готовности ручных ok — как есть + набор no-hunting.
6. **Predajňa:** география A, конец 21.12, 10 €/день, минусы.
7. **Включение в один момент:** все готовые SO27 (термо — когда есть хотя бы один ручной ok в наличии).
8. **Через ≤ 72 ч по каждому пулу:** показы/клики нового, покрытие, ошибки трекинга → старый пул PAUSED (не удалять); неготовый — разбор, без продления параллели сверх allowance.
9. **Ежедневно оператор:** search terms, география, наличие, ошибки, темп по потолку T.

## 9. Статусы
| ID | Статус после хода 7 |
|---|---|
| R5-CHATGPT-01/09/12/13 | исправлено в repo v3.1, 100/100 тестов; не live |
| R5-CHATGPT-02 | шаг 1 плана, после деплоя |
| R5-CHATGPT-04 | патч label3 + дерево; факт: <20 € в Merchant не отправляются |
| R5-CHATGPT-05 | T=5300 разложен, payloads, validate_only до создания |
| R5-CHATGPT-06 | реальный account-level diff + наборы, 59/59 fixtures |
| R5-CHATGPT-14 | Junior/catch-all разведены, 0 пересечений на 7 828 товарах |
| R5-CHATGPT-15 | smart CSV исправлен, 40/6 |
| R5-CODE-12 | **отозвано Code** — ошибка, список существует |
| R5-CODE-13 | продление Predajňa — в плане §8 п. 6 |

## 10. Передача ChatGPT (ход 8, `08_chatgpt_prelaunch_check.md`)
Короткая техническая приёмка по чек-листу: (1) прогнать 6 тестовых файлов на AdsGate v3.1 и попытаться сломать миграцию/транзакцию; (2) negatives_effective.py — diff и fixtures против повторного чтения account-level списка; (3) so27_listing_trees.json + coverage_matrix — единственный лист, исключение review/hold/цены; (4) budget_plan_T5300 = 5300 и payloads; (5) план исполнения §8 — порядок и откат. Не возвращать недельные волны и не спрашивать владельца заново о бюджете.
