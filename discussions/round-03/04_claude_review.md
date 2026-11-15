# Claude Cowork — круг 03 — 2026-11-15
- **Версия / SHA:** HEAD main `7d10164` («Publish Cowork round three handoff and adopt three-participant review protocol»). Снимок каталога `data/catalog/2026-11-14`. Методика `markets/sk/05_budget_and_roas.md` v1. Приоритет `markets/sk/06_model_query_visibility.md`. Рабочий отзыв, а не утверждённая стратегия и не разрешение менять кабинеты.
- **Прочитанные файлы:** `PROTOCOL.md` (редакция 15.11, три участника); `README.md`; `discussions/STATUS.md`; `discussions/ISSUES.md`; `discussions/template_review.md`; `discussions/round-03/02_gemini_review.md`; `discussions/round-03/03_chatgpt_handoff_to_claude.md`; `discussions/round-02/02_grok_review.md`, `02a_…`, `03_gemini_review.md`, `03a_…`; `discussions/round-01/04_claude_review.md`, `05_chatgpt_summary.md`; `markets/sk/05_…`, `06_…`; каталог (все `assortment-*`, `merchant-*`, `scope-candidates.json`) и CSV круга 1.
- **Перенос круга 2:** мой ответ за круг 2 в репозиторий не попал (это подтверждено в `03_chatgpt_handoff_to_claude.md`). Он приложен без изменений как `04_claude_attachments/carryover_round02_claude_review.md`. Ниже — только то, что из него остаётся в силе или исправлено. Это не попытка выдать его за опубликованный в срок ответ.
- **Внешние проверки 15.11.2026 (первичные или официальные источники):** приоритет Standard Shopping; channel prioritization; минус-слова; приоритет идентичных ключей; лимиты RSA; `shopping_product` в Google Ads API; Merchant API в скриптах Google Ads и закрытие Content API for Shopping.
- **Недоступные материалы:** живые Google Ads и Merchant, PaidSync, COGS, логистика, возвраты, CRM, скриншоты владельца. Все экономические числа — сценарии, кроме цен из снимка Merchant.
- **Предыдущий участник:** Gemini (`02_gemini_review.md`) + модератор (`03_chatgpt_handoff_to_claude.md`).
- **Следующий участник:** ChatGPT.

## Резюме
1. **Shopping (R3-CHATGPT-01):** приоритета High/Low между product groups внутри одной кампании нет. Приоритет — это настройка Standard Shopping-кампании и действует между кампаниями с одинаковыми товарами. Бюджет есть у кампании (или общий), но не у группы товаров. Channel prioritization — другой инструмент: распределение между площадками (для Shopping это Google Search и поисковые партнёры), а не между товарами. **Рекомендую:** одну пилотную Standard Shopping-кампанию с приоритетом выше старых; одна группа объявлений = один SKU для контрольных моделей и их вариантов; все остальные допустимые модели остаются в действующих кампаниях, покрытие не сужается.
2. **Search (R3-CHATGPT-02/03):** четыре полные группы с реальными URL, exact/phrase-ключами, минус-словами с указанным типом соответствия и валидными RSA (6–8 заголовков ≤30, 2 описания ≤90, H1 закреплён). Цена и «Skladom» вынесены в условные ассеты, пока нет синхронизации. Симулятор маршрутов: 24 из 24 тестов дают ожидаемый результат, но только по буквальной логике; близкие варианты Google не моделируются.
3. **Каталог (R3-CHATGPT-04):** числа Gemini круга 3 (4 204 / 1 397 / 402 / 7 868 и др.) **воспроизводятся точно** — я пересчитал из исходников. Претензии к Gemini другие: нет кода и построчного CSV; группа «ложные срабатывания» скрывает, что 5 из 8 SKU в наличии; REST склеивает 1 776 URL с названием и 6 092 без. Приложены скрипт, построчный CSV на 14 716 строк и таблица соответствия.
4. **Пилот (R3-CHATGPT-05):** отбор «по высокому CTR» и откат «CPA выше цели 7 дней» отклоняю. У четырёх контрольных SKU 14 кликов за 30 дней — CPA за неделю не определён. Видимость (допуск → показы → запросы) измеряется за дни, экономика — только по когорте и после окна задержки конверсий.
5. **Новый технический факт:** Content API for Shopping закрыт 18.08.2026. Любая синхронизация наличия для Search должна строиться на Merchant API (доступен в скриптах Google Ads как Advanced API). Запросы Gemini круга 2 к «Content API» устарели.

Консенсус не объявляю. Рекламу, фиды и сайт не меняю.

## Поддерживаю
- **ChatGPT, R3-CHATGPT-01…05:** все пять замечаний подтверждаю. Доказательства — в таблице «Критика» и вложениях.
- **Gemini, круг 3, раздел 1:** признание, что разница показов Vegas/New Vegas — корреляция, а отсутствие GTIN в экспорте ничего не доказывает. Отказ от прогноза 65–75 % и множителей бюджета (раздел 5).
- **Gemini, круг 3, раздел 4:** арифметика групп верна (см. `gemini_r3_crosswalk.csv`).
- **Gemini, круг 3, раздел 5:** учитывать задержку конверсий — верно. Но вывод (откат через 7 дней) этому противоречит.

## Критика и риски

| ID | Чей тезис / файл | Критичность | Факт / гипотеза / нет данных | Риск и доказательство | Исправление | Как проверить |
| --- | --- | --- | --- | --- | --- | --- |
| R3-CLAUDE-01 | Gemini r3, раздел 2: High/Low внутри кампании на уровне product groups; бюджет High-группы с переносом на Low | блокирующее для Shopping-раздела Gemini | **ФАКТ** | В справке Google приоритет описан для случая, когда один товар рекламируется в нескольких Shopping-кампаниях; при исчерпании бюджета кампании с высоким приоритетом ставку делает следующая ([справка](https://support.google.com/google-ads/answer/6275296)). Механизма «группа High → группа Low» внутри кампании нет. | Архитектура — Результат 1. Уровни управления: кампания (бюджет, приоритет, стратегия, фильтр ассортимента, минусы, гео, расписание); группа объявлений (ставка, минусы); product group (ставка только при ручной CPC). | ChatGPT: выгрузка E1/E2 подтверждает тип кампаний и доступные поля. |
| R3-CLAUDE-02 | Gemini r3, раздел 2: минусы «teleskop, ďalekohľad, cena» на уровне кампании | блокирующее | **ФАКТ** (механика) | В кампании со всем каталогом широкие минусы режут «ďalekohľad leica trinovid 10x42», «teleskop sky-watcher 150pds eq3», все запросы с ценой и все общие запросы. Это противоречит цели `06_`. | Общие слова как минусы — только точного соответствия и только по данным поисковых запросов. Коммерческие слова (cena) не минусовать. | `shopping_query_routing_tests.csv` (Q02, Q03, Q17); Ad Preview. |
| R3-CLAUDE-03 | Gemini r3, раздел 3: Broad + Phrase, минусы phrase «cena/teleskop/ďalekohľad», 2 заголовка | блокирующее для Search-раздела | **ФАКТ** | Широкое соответствие точной модели выведет объявление на соседние модели (8×42, Ultravid). Минус-фраза «ďalekohľad» блокирует «ďalekohľad leica trinovid 10x42 hd». RSA требует минимум 3 заголовка ([справка](https://support.google.com/google-ads/answer/7684791)). | Четыре группы — Результат 2: exact + phrase; минусы — только соседние размеры, комплектации и поколения; RSA 6–8 заголовков. | `search_routing_results.csv`, `search_rsa.csv`. |
| R3-CLAUDE-04 | Gemini r3, раздел 4 («воспроизводимый расчёт», просьба проверить SQL) | существенное | **ФАКТ** | Числа совпадают, но кода, CSV и SQL нет, поэтому проверить состав групп нельзя. M_FALSE_TRIGGER смешивает флаг названия с наличием: 5 из 8 SKU в наличии. REST склеивает 1 776 и 6 092 URL. | Принять 8 корзин Claude (MC/ST) с флагами. Группы Gemini — как производную разметку. SQL не писать без схемы CS-Cart. | `catalog_audit.py`, `catalog_buckets.csv`, `gemini_r3_crosswalk.csv`. |
| R3-CLAUDE-05 | Gemini r3, раздел 5: пилот «по высокому CTR», откат «CPA > Target 7 дней» | блокирующее для приёмки | **ФАКТ** (объёмы 02a) | За 30 дней у 4 SKU: 116/972/48/83 показа и 0/12/1/1 кликов. CTR при 1 клике — шум; отбор по высокому CTR завышает ожидания (регрессия к среднему) и подменяет цель охвата моделей. CPA за 7 дней при 0–3 кликах не определён, целевого CPA без маржи нет. | Когорта — по цели (контрольные модели + варианты + модели со спросом). Видимость — за 2–5 дней по когорте; экономика — после окна задержки (Результат 4). | E4 + E8 (`conversion_lag_bucket`). |
| R3-CLAUDE-06 | Синхронизация наличия для Search (Gemini r2: «Page Feed / Customizer»; запрос через «Content API») | существенное | **ФАКТ** | Content API for Shopping закрыт 18.08.2026; [Merchant API доступен в скриптах Google Ads как Advanced API](https://developers.google.com/ads/blog/posts/2026/04/merchant-api-is-coming-to-google-ads). `shopping_product.status` [обновляется до 24 ч](https://developers.google.com/google-ads/api/fields/v17/shopping_product). Customizer и page feed группы на паузу не ставят. | ТЗ скрипта: метка `oid:<offerId>` на группе → Merchant API (products/productstatuses) → пауза или включение → журнал и уведомление; первая неделя в режиме без изменений. До внедрения — без «Skladom» и статической цены. | Тест в режиме без изменений: SKU в OOS → в журнале появляется «pause». |
| R3-CLAUDE-07 | Channel prioritization как средство управления товарами (риск путаницы, R3-CHATGPT-01) | улучшение | **ФАКТ** | [Channel prioritization](https://blog.google/products/ads-commerce/channel-prioritization-budget-allocation/) задаёт приоритет площадок (поиск, партнёры, КМС) и долю бюджета, а не товаров или запросов. Внедряется постепенно, при tROAS/tCPA без ограничения бюджетом почти не влияет на расход. | Не использовать для модельной маршрутизации. Для Shopping — опционально держать поисковых партнёров на низком приоритете (решение владельца, после проверки в аккаунте). | E1: есть ли настройка в аккаунте. |
| R3-CLAUDE-08 | Моя рекомендация (пилотная кампания с группами по SKU) | существенное | **ГИПОТЕЗА** (риск собственной схемы) | Пилотные SKU будут показываться и по общим запросам («ďalekohľad 10x42») по ставкам модельной группы — возможен дорогой общий трафик. | Ставка группы ≤ экономического потолка SKU; ежедневный просмотр запросов групп; точные минусы общих запросов только по фактам; этап B (разделение запросов) — если доля общих запросов в расходе стабильно высока. | E5 по группам пилота. |
| R3-CLAUDE-09 | Маршрут неоднозначного запроса «levenhuk vegas ed 10x42» | существенное | **НЕТ ДАННЫХ** (решение владельца) | Запрос не указывает поколение. В моём проекте он идёт в группу 26113 (буквальное название товара), «new» — в 103640. Альтернатива — отдавать его 103640 (дешевле, новее). Экономически 103640 выгоднее только при CR в 1,7–2 раза выше. | По умолчанию — 26113. Переключение — решение владельца или эксперимент Google Ads, не дубли ключей. «levenhuk vegas 10x42» (без ED) в Search не маршрутизирован, его покрывает Shopping. | `search_routing_results.csv` T08/T13; `unit_economics_4sku.csv`. |
| R3-CLAUDE-10 | Процесс: ответ Claude за круг 2 не опубликован; в корне лежит `claude_round01_upload.zip` | улучшение | **ФАКТ** | Gemini в круге 3 не видел исправлений круга 2 и повторил часть ошибок (минусы, бюджет HIGH). Zip в корне — дубль круга 1. | ChatGPT: опубликовать `carryover_round02_claude_review.md` как исторический документ (с пометкой даты) или сослаться на вложение; удалить zip. | `git ls-files`. |

### Red Teaming собственной работы
1. **Симулятор маршрутов** проверяет только буквальную логику: идентичный exact, вхождение фразы, минусы broad/phrase/exact, нормализацию «10 x 42»→«10x42» и «-»→пробел. Две последние нормализации — мои **допущения**. Google может сопоставить запрос с ключом как близкий вариант там, где симулятор говорит NONE. Поэтому до запуска обязательна проверка в Ad Preview & Diagnosis (E11), а после — по поисковым запросам.
2. **Тексты RSA** используют только факты из названий товаров (кратность, диаметр, ED, 150/750, EQ3, двухскоростная фокусировка, алюминиевый штатив). «Na pozorovanie prírody» и «Prémiová optika Leica» — маркетинговые формулировки, их подтверждает владелец. Словацкий текст стоит вычитать носителю.
3. **Пилот с приоритетом High** перехватывает ставку у старых кампаний по пилотным SKU сразу после включения. Если новая кампания окажется ограничена бюджетом, показы этих SKU снова пойдут из старых кампаний (до шага исключения) — это защита от разрыва, но она искажает измерения первых дней.

## Ответ на предыдущие позиции

| ID замечания | Согласен / оспариваю | Причина и источник | Предлагаемый статус |
| --- | --- | --- | --- |
| R3-CHATGPT-01 | Согласен | R3-CLAUDE-01, R3-CLAUDE-07; Результат 1 | закрыть после проверки ChatGPT |
| R3-CHATGPT-02 | Согласен | R3-CLAUDE-02/03; таблицы маршрутов Shopping (22) и Search (24) | закрыть после Ad Preview (E11) |
| R3-CHATGPT-03 | Согласен | Результат 2: 4 группы, URL, ключи, минусы, RSA | исправлено, ждёт проверки ChatGPT и вычитки текстов |
| R3-CHATGPT-04 | Согласен частично | Числа Gemini верны; не хватало кода и CSV — приложены | исправлено, ждёт проверки ChatGPT |
| R3-CHATGPT-05 | Согласен | R3-CLAUDE-05; Результат 4 | исправлено, ждёт проверки |
| R2-GEMINI-02 | Без изменений | Отсутствие GTIN в экспорте ≠ отсутствие в фиде; проверка через Merchant API (E10), не Content API | открыто |
| R2-GEMINI-03 | Без изменений | Причинность Vegas не доказана; R3-CLAUDE-09 | открыто |
| R2-GEMINI-04 | Дополнено | +3 варианта 150P (47489/47426/47474); минусы по комплектации в Search | открыто до проверки запросов |
| R2-GEMINI-05 | Исправлено | `catalog_audit.py` | закрыть |
| R2-GROK-01…07 | Позиции круга 2 без изменений | Grok больше не обязательный участник; его замечания остаются в реестре. R2-GROK-05 (ассортимент) — матрица не исключает модели по цене; R2-GROK-06 (freeze) — решение владельца | по `ISSUES.md` |
| R1-CHATGPT-04 | Согласен | Проверочный пример `05_` пересчитан: CM_exp 24,8; пороги 3,629/4,032 | закрыть |
| R1-CHATGPT-05 | Согласен | CR = покупки/рекламные клики во всех моих расчётах | закрыть для методики |
| R1-CHATGPT-07 | Согласен | Моё «маскирует функцию» (Krypton 2 XG50) было слишком сильным | открыто (сверка комплекта) |
| R1-CLAUDE-01…08 | См. ниже «Мои ошибки» | — | по `ISSUES.md` |

**Мои ошибки круга 1 (признаю и исправляю):**
1. Max CPC через CR сайта (покупки/сессии). Правильно — покупки/рекламные клики (`05_`, R1-CHATGPT-05).
2. «Если загружены корректировки возвратов, r из формулы убирается» — неверно. Возврат остаётся экономической потерей (`05_`, R1-CHATGPT-04).
3. «Название Krypton 2 XG50 скрывает clip-on функцию» — слишком сильно. Производитель называет XG50 монокуляром с опциональной насадкой; нужна сверка комплекта (R1-CHATGPT-07).
4. «≈95 % точности» по выборке из 60 строк — отзываю как метрику.
5. Медианы цен использованы как средний чек (R1-CLAUDE-07). В этом круге расчёт — на заказ из одной позиции, это явно оговорено.

---

## Контрпредложение

### Результат 1. Исполнимая архитектура Shopping

**Фактически доступные рычаги (проверено по справке Google и документации API 15.11.2026):**

| Уровень | Что можно задать | Чего нет |
| --- | --- | --- |
| Кампания Standard Shopping | Бюджет (дневной, общий или общий на период 3–90 дней); **приоритет Low/Medium/High**; стратегия ставок; фильтр ассортимента (listing scope); минус-слова и списки минусов; гео; расписание; channel prioritization (поиск / партнёры — по мере внедрения) | Приоритета между группами товаров |
| Группа объявлений | Ставка по умолчанию; минус-слова; дерево групп товаров | Бюджета |
| Группа товаров (product group) | Ставка (только при ручной CPC); исключение | Бюджета, приоритета, минус-слов |
| PMax | Листинговые фильтры asset group, минус-слова и исключения брендов на уровне кампании | Приоритета над Standard Shopping: при пересечении решает Ad Rank |

**Рекомендуемый вариант (этап A):**
- `SK_SHOP_Models_Pilot` — новая Standard Shopping-кампания, приоритет **выше**, чем у старых кампаний с теми же товарами.
- Группы объявлений: **одна на SKU** для 4 контрольных моделей и их вариантов в наличии. По `control_sku_variants.csv` это 22 SKU: 6 Trinovid, 9 Vegas/New Vegas, 7 из 150-й серии. Дерево в группе: `item_id = X` — включён, всё остальное — исключено.
- Минус-слова: на старте только кампанийные «bazár/bazar/použitý/pouzity» (broad). Общие слова — только точного соответствия и только после просмотра реальных запросов.
- Ставки: ручная CPC на группу ≤ экономического потолка SKU (Результат 3) после получения маржи. Автоматические стратегии — после закрытия R1-CHATGPT-02.
- **Все остальные допустимые модели** остаются в действующих кампаниях (покрытие не сужается). Расширение — семейство за семейством, по данным пилота.

**Альтернативы (кратко):**

| Вариант | Плюсы | Минусы | Вывод |
| --- | --- | --- | --- |
| Разделение запросов: 2–3 кампании High/Medium/Low с одинаковыми товарами | Разделяет общие и модельные запросы | Утечка общих запросов при исчерпании бюджета High; минусы не ловят варианты написания; широкие общие минусы блокируют модельные запросы (Q02/Q03/Q17) | Этап B — только для семейств, где данные этапа A покажут дорогой общий трафик |
| PMax только с фидом | Меньше ручной работы, все площадки | Нет связки запрос→товар; поисковые запросы по категориям; смешение площадок | Не для контроля видимости моделей |
| Gemini r3 (High/Low внутри кампании) | — | Механизма не существует (R3-CLAUDE-01) | Отклонить |

**Сценарии для рекомендуемого варианта:**

| Сценарий | Что происходит | Что видим в данных | Риск / мера |
| --- | --- | --- | --- |
| Точная модель («leica trinovid 10x42 hd») | Ставка — из пилотной кампании (приоритет выше), товар 103933 из своей группы | Запросы группы AG_103933 (если выше порога приватности) | Проигрыш по Ad Rank → потерянная доля показов из-за рейтинга по группе |
| Общий запрос («ďalekohľad 10x42») | Google может показать любой подходящий товар; для пилотных SKU — по ставке их группы | Общие запросы в отчётах групп пилота | R3-CLAUDE-08: потолок ставки, точные минусы по фактам |
| Цена + модель («… cena») | Не блокируется (минуса «cena» нет) | Запрос в группе модели | — |
| Соседний вариант (8×42 вместо 10×42; GoTo вместо EQ3) | Варианты в отдельных группах; товар выбирает Google по релевантности фида | Видно, какая группа получила запрос | Если показывается не тот вариант — проверить title/атрибуты фида, а не минусы |
| Бюджет пилотной кампании исчерпан | **До шага T6:** ставка переходит к старой кампании (приоритет ниже) — разрыва нет. **После T6:** пилотные SKU не показываются до следующего дня | Потерянная доля показов из-за бюджета > 0 у пилотной кампании | Ежедневный контроль; бюджет пилота ≥ наблюдаемого спроса когорты |
| SKU не в наличии | Merchant: не допущен (out of stock), карточки нет | `shopping_product.status` = NOT_ELIGIBLE с проблемой наличия | Search-группа продолжит показ до внедрения скрипта (R3-CLAUDE-06) |

### Результат 2. Четыре образца модельного Search
Файлы: `search_keywords.csv`, `search_negatives.csv`, `search_rsa.csv`, `search_routing_results.csv`, генератор и проверки — `search_spec.py`.

| Группа | Final URL | Exact | Phrase | Минусы группы (тип) |
| --- | --- | --- | --- | --- |
| AG_103933 Leica Trinovid 10×42 HD | https://sonataoptics.sk/leica-trinovid-10x42-hd-alekohlad.html | leica trinovid 10x42 hd; leica trinovid hd 10x42; trinovid 10x42 hd; leica trinovid 10x42; ďalekohľad leica trinovid 10x42 | trinovid 10x42; trinovid hd 10x42 | PHRASE: 8x42, 10x32, 8x32, 10x25, 8x20. BROAD: bca, ultravid, noctivid, geovid, retrovid, monokulár, monokular |
| AG_26113 Levenhuk Vegas ED 10×42 | https://sonataoptics.sk/levenhuk-vegas-ed-10x42-binoculars.html | levenhuk vegas ed 10x42; vegas ed 10x42; ďalekohľad levenhuk vegas ed 10x42 | levenhuk vegas ed 10x42 | BROAD: new, nový, novy, monokulár, monokular, monocular. PHRASE: 8x42, 10x50, 12x50, 10x56, 12x56 |
| AG_103640 Levenhuk New Vegas ED 10×42 | https://sonataoptics.sk/levenhuk-new-vegas-ed-10x42-binokular.html | levenhuk new vegas ed 10x42; new vegas ed 10x42; ďalekohľad levenhuk new vegas ed 10x42 | new vegas ed 10x42 | PHRASE: 8x42, 10x50, 12x50, 10x56, 12x56. BROAD: monokulár, monokular, monocular |
| AG_47420 Sky-Watcher Explorer-150PDS EQ3 | https://sonataoptics.sk/skywatcher-teleskop-n-150-750-pds-explorer-bd-eq3.html | sky watcher explorer 150pds eq3; skywatcher explorer 150pds eq3; explorer 150pds eq3; sky watcher 150pds eq3; skywatcher 150pds eq3; teleskop sky watcher 150pds eq3 | 150pds eq3; 150 pds eq3 | BROAD: goto, synscan, eq5, ota, tubus, 150p, 150pl, 1200, heritage, dobson, 150i. PHRASE: eq3 pro, star discovery |

Минус-слова кампании: BROAD bazár, bazar, použitý, pouzity. **«cena», «ďalekohľad», «teleskop» не минусуются.** Минус-слова [не покрывают близкие варианты](https://support.google.com/google-ads/answer/12437241), поэтому формы с диакритикой и без указаны отдельно там, где это важно.

**RSA (длина проверена программой, 0 нарушений):**

| Группа | Заголовки (≤30), H1 закреплён | Описания (≤90) | Пути (≤15) |
| --- | --- | --- | --- |
| 103933 | **Leica Trinovid 10×42 HD** (23); Binokulárny ďalekohľad Leica (28); Zväčšenie 10×, objektív 42 mm (29); Prémiová optika Leica (21); Na pozorovanie prírody (22); Kúpte v Sonata Optics (21); Obchod s optikou (16); Trinovid HD 10×42 online (24) | Leica Trinovid 10×42 HD – binokulárny ďalekohľad. Parametre a cenu nájdete na webe. (83); Objednajte online v Sonata Optics, obchode s optikou. (53) | Leica / Trinovid-10x42 |
| 26113 | **Levenhuk Vegas ED 10×42** (23); Binokulárny ďalekohľad 10×42 (28); Optika s ED sklom (17); Zväčšenie 10×, objektív 42 mm (29); Kúpte v Sonata Optics (21); Obchod s optikou (16) | Levenhuk Vegas ED 10×42 – binokulárny ďalekohľad s ED sklom. Parametre a cena na webe. (86); Objednajte online v Sonata Optics, obchode s optikou. (53) | Levenhuk / Vegas-ED-10x42 |
| 103640 | **Levenhuk New Vegas ED 10×42** (27); Nová rada Vegas ED (18); Binokulárny ďalekohľad 10×42 (28); Optika s ED sklom (17); Zväčšenie 10×, objektív 42 mm (29); Kúpte v Sonata Optics (21) | Levenhuk New Vegas ED 10×42 – binokulárny ďalekohľad s ED sklom. Parametre na webe. (83); Objednajte online v Sonata Optics, obchode s optikou. (53) | Levenhuk / New-Vegas-10x42 |
| 47420 | **Sky-Watcher 150PDS EQ3** (22); Explorer-150PDS na montáži EQ3 (30); Newtonov reflektor 150/750 (26); Dvojrýchlostné zaostrovanie (27); Hliníkový statív v balení (25); Kúpte v Sonata Optics (21); Obchod s optikou (16) | Sky-Watcher Explorer-150PDS 150/750 na montáži EQ3 s hliníkovým statívom. (73); Manuálna montáž EQ3, bez GoTo. Objednajte online v Sonata Optics. (65) | Sky-Watcher / 150PDS-EQ3 |

**Условные ассеты (не включать до синхронизации):** «Cena {CUSTOMIZER.cena}» — только из того же источника, что и цена на посадочной; «Skladom» — только при работающем скрипте наличия и подтверждённом владельцем сроке отправки. В текстах нет обещаний доставки, гарантии и адреса шоурума — их подтверждает владелец.

**Маршруты Search (`search_routing_results.csv`):** 24 теста, все соответствуют ожиданию. Ключевые:
- T02 «leica trinovid 10x42 hd cena» и T03 «ďalekohľad leica trinovid 10x42» → группа 103933 (в проекте Gemini оба были бы заблокированы).
- T05 8×42, T06 10×25 BCA → заблокированы минусами 103933.
- T12 «new vegas ed 10x50» → заблокирован в обеих группах Vegas.
- T16 GoTo, T17 150P, T19 SynScan/EQ3 Pro, T20 OTA → заблокированы в 47420.
- T13 «levenhuk vegas 10x42» → не маршрутизирован намеренно (R3-CLAUDE-09).

**Синхронизация наличия:** R3-CLAUDE-06. Search и Shopping по одному запросу могут показываться одновременно — это разные форматы, их измеряют раздельно.

### Результат 3. Воспроизводимая матрица каталога
Файлы: `catalog_audit.py` (входы — только файлы репозитория; проверки: 14 716 уникальных URL, 6 077 уникальных offerId, все ссылки Merchant есть в sitemap), `catalog_buckets.csv` (по одной строке на URL; флаги `availability`, `brand_filled`, `policy_review`, `false_trigger_title`, `weapon_candidate_heuristic`, `in_scope_candidates`), `catalog_bucket_summary.csv`, `gemini_r3_crosswalk.csv`.

| Корзина | URL | Соответствие Gemini r3 |
| --- | ---: | --- |
| MC-1 Merchant, проверка по политике (2 в наличии: 107817, 107671; 5 OOS) | 7 | M_RISK_HIGH_MED 7 ✔ |
| MC-2 Merchant, в наличии, бренд заполнен | 4 209 | M_IN_STOCK_WITH_BRAND 4 204 + 5 из M_FALSE_TRIGGER ✔ |
| MC-3 Merchant, в наличии, без бренда | 59 | 59 ✔ |
| MC-4 Merchant, OOS, бренд заполнен | 1 397 | 1 397 ✔ |
| MC-5 Merchant, OOS, без бренда | 405 | M_OOS_NO_BRAND 402 + 3 из M_FALSE_TRIGGER ✔ |
| ST-1 только сайт, эвристический кандидат оружейной оптики (не подтверждённое нарушение) | 771 | 771 ✔ |
| ST-2 только сайт, название известно | 1 776 | REST 7 868 = ST-2 + ST-3 ✔ |
| ST-3 только сайт, нет названия, цены и наличия | 6 092 | ↑ |
| **Итого** | **14 716** (Merchant 6 077) | 14 716 ✔ |

Вывод: числа Gemini верны. Разметка Claude сохраняет наличие для 8 ложных срабатываний и разделяет хвост по наличию данных. 778 URL (7 в Merchant + 771 на сайте) — эвристические кандидаты, роли не подтверждены. SQL не пишу: схема CS-Cart неизвестна, спецификация выгрузки — `cscart_export_spec.csv`.

### Результат 4. Экономика и приёмка пилота
**Независимая проверка методики `05_`:** пример пересчитан (CM_exp = 0,9×40 − 2 − 5 − 3 − 0,1×12 = 24,8; V = 90; 90/24,8 = 3,629; 100/24,8 = 4,032) — сходится. Возврат остаётся в CM_exp как потеря. База ROAS: скорректированный value ↔ порог V/CM_exp; value до возвратов ↔ P_n/CM_exp. Смешивать нельзя.

**Четыре SKU** (`unit_economics_4sku.py/.csv`; допущения: DPH 23 %, комиссия 1,5 % от суммы с DPH, бесплатная доставка покупателю, логистика и возвраты — сценарий; стресс: возвраты ×2, обратную доставку оплачивает магазин). Маржа 25 %, базовый сценарий:

| offerId | CM_exp | BE ROAS (скорр.) | Max CPC при CR рекламы 1 / 2 / 3 % |
| --- | ---: | ---: | --- |
| 103933 Trinovid 10×42 HD (1 275 €) | 215,23 € | 4,62 | 2,15 / 4,30 / 6,46 € |
| 26113 Vegas ED 10×42 (329,95 €) | 49,50 € | 5,15 | 0,50 / 0,99 / 1,49 € |
| 103640 New Vegas ED 10×42 (209,95 €) | 28,50 € | 5,69 | 0,28 / 0,57 / 0,85 € |
| 47420 150PDS EQ3 (697,22 €) | 87,23 € | 6,17 | 0,87 / 1,74 / 2,62 € |

Маржа 15 и 35 % и стресс — в CSV. Это сценарии, а не ставки запуска. Реальная доставка 150PDS EQ3 сильнее всего влияет на результат.

**Почему пилот нельзя оценивать «по CPA за 7 дней»:** 4 SKU дали 1 219 показов и 14 кликов за 30 дней. При CR рекламы 2 % это ≈0,3 покупки в месяц. Видимость измерима быстро: чтобы различить падение показов на 30 % на уровне 99 %, нужно ≈74 ожидаемых показа ((2,58/0,3)², распределение Пуассона) — у этих 4 SKU это ≈2 дня. Экономика одной модели за недели неизмерима, оценивать её можно только по когорте после окна задержки конверсий.

**Когорта:** 22 SKU из семейств контрольных моделей (`control_sku_variants.csv`, в наличии) + до 10–30 SKU с наибольшими показами за 90 дней (E4), чтобы набрать объём. **Контрольная группа:** похожие SKU без переноса (поправка на сезон Black Friday / Рождество). Отбор по CTR не используется.

**Переход (шаги T0–T9, подробности — `carryover_round02_claude_review.md`, Результат 4):**

| Шаг | Действие | Проверка после шага | Откат |
| --- | --- | --- | --- |
| T0 | Read-only выгрузки E1–E10; снимок дерева listing groups старых кампаний (JSON, хеш) | Снимок сохранён | — |
| T1 | Карта: в каких кампаниях допущен каждый SKU когорты (`shopping_product` по кампании) | Таблица SKU × кампания | — |
| T2 | Пилотная кампания создана **на паузе**, приоритет выше старых | `shopping_product` по пилоту = только когорта | Удалить черновик |
| T3 | Маршруты Shopping (Q01–Q20) и Search (T01–T24) в Ad Preview | Расхождения задокументированы | Не включать |
| T4 | **Включить пилот**, старые кампании не трогать | ≤24 ч: ELIGIBLE/ELIGIBLE_LIMITED для 100 % SKU когорты в наличии | Пауза пилота (старые работают — разрыва нет) |
| T5 | 48–72 ч наблюдения | Показы когорты идут из пилота; в старых по когорте ≈0 | Пауза пилота |
| T6 | Исключить когорту в старых кампаниях по item_id | Старые кампании не возвращают SKU когорты | Восстановить дерево из снимка T0 |
| T7 | Search-группы (без условных ассетов) | Объявления одобрены; запросы соответствуют моделям | Пауза групп |
| T8 | Мониторинг ≥28 дней или до окна задержки конверсий (что дольше) | Уровни 1–4 | — |
| T9 | Решение: расширять / этап B / откат | По критериям | T6 в обратную сторону |

Операции не атомарны. Порядок «сначала включить новое, потом исключить старое» плюс приоритет кампании исключают разрыв. Временное пересечение безопасно, потому что ставку делает кампания с высоким приоритетом. Для PMax этот порядок не работает (там решает Ad Rank) — при пересечении с PMax нужна отдельная проверка на T1.

**Уровни приёмки (раздельно):**
1. **Допуск:** `shopping_product.status` по пилоту = ELIGIBLE/ELIGIBLE_LIMITED.
2. **Показы товара:** `shopping_performance_view` по SKU в пилоте; если их нет — код причины (наличие / нет спроса за период / рейтинг / бюджет).
3. **Показы по запросу:** модельный запрос в `search_term_view` группы с одним SKU. Если запроса нет — `insufficient_data` (порог приватности), а не провал.
4. **Экономика:** вклад когорты против контрольной группы после окна задержки конверсий.

**Триггеры отката:**
- **Технический:** уровень 1 не выполнен через 24 ч после T4, или у SKU в наличии нет допуска ни в одной кампании после T6.
- **Статистический (только по когорте):** наблюдаемые показы < E − 2,58·√E три дня подряд, где E — базовые показы за те же дни недели × изменение контрольной группы. Для отдельного SKU с ожидаемыми <30 показами за период триггер не применяется.

### Результат 5. Передача ChatGPT
**Исправлено в этом круге:** механика приоритетов (R3-CHATGPT-01); маршруты и типы соответствия (02); четыре Search-группы с RSA (03); воспроизводимая матрица и сверка чисел Gemini (04); когорта, сроки и приёмка (05); собственные ошибки круга 1.

**Готово к проверке ChatGPT:** все файлы `04_claude_attachments/` (скрипты запускаются без сети, только по файлам репозитория).

**Условно:**
- Цены и «Skladom» в RSA — после синхронизации.
- Маршрут «vegas ed 10x42» — решение владельца.
- Этап B (разделение запросов) — после данных этапа A.
- Ставки и бюджет — после маржи.
- Тексты — вычитка носителем словацкого и подтверждение владельцем.

**Блокирует запуск:** R1-CHATGPT-02 (цели конверсии); выгрузки E1–E3, E7, E10 не получены; маржа и логистика; решение по MC-1 (107817 и 107671 в наличии); freeze как запрет записи; окно сезона.

**Read-only выгрузки (без выдуманных связок запрос→offerId):**

| # | Ресурс | Поля | Период | Назначение |
| --- | --- | --- | --- | --- |
| E1 | `campaign`, `campaign_budget`, `campaign_criterion` (location, ad_schedule) | type/sub_type, status, shopping_setting.campaign_priority, merchant_id, feed_label, bidding_strategy_type, target_roas, budget amount_micros, delivery_method; наличие channel prioritization | текущее | Кто конкурирует за товары; приоритеты |
| E2 | `campaign_criterion` LISTING_SCOPE; `ad_group_criterion` LISTING_GROUP; `asset_group_listing_group_filter` | case_value (item_id/brand/custom_attribute), negative, cpc_bid_micros, status | текущее | Карта пересечений; снимок для отката |
| E3 | `shopping_product` в области каждой кампании | item_id, status, issues, availability, effective_max_cpc | текущее | Уровень 1 приёмки |
| E4 | `shopping_performance_view` по дням | date, product_item_id, campaign.id, ad_group.id, product_custom_attribute0–4, impressions, clicks, cost_micros, conversions, conversions_value | 17.08–14.11 (90 дн.) | Базовая линия когорты, уровень 2 |
| E5 | `search_term_view` (Shopping и Search) | search_term, campaign.id, ad_group.id, impressions, clicks, cost_micros, conversions | 90 дн. | Уровень 3 — только по группам; соединения с offerId нет |
| E6 | `campaign` по дням | search_impression_share, budget_lost, rank_lost, absolute_top_IS, cost | 90 дн. | Связь расход ↔ показы вместо коэффициентов |
| E7 | Минус-слова: campaign/ad_group criterion, `shared_set` + `shared_criterion`, customer-level | text, match_type, уровень | текущее | Конфликты минусов |
| E8 | `conversion_action`, `customer_conversion_goal`, `campaign_conversion_goal`, `custom_conversion_goal`; `segments.conversion_lag_bucket` | status, category, primary_for_goal, origin, counting_type, value settings, окна; задержка | текущее + 90 дн. | R1-CHATGPT-02; длительность пилота |
| E9 | `change_event` | change_date_time, resource_type, operation, changed_fields | последние 30 дн. | Что меняли до пилота |
| E10 | **Merchant API** products + productstatuses (не Content API) | offerId, gtin, mpn, identifierExists, brand, customLabel0–4, productTypes, googleProductCategory, availability, price, included/excludedDestinations, feedLabel, contentLanguage; destinationStatuses (SK), itemLevelIssues | текущее; минимум 32 строки `control_sku_variants.csv` | Реальные идентификаторы и проблемы |
| E11 | Ad Preview & Diagnosis | скриншоты маршрутов Q01–Q20 и T01–T24, Словакия, мобильные и десктоп | разово до T4 | Проверка маршрутов без влияния на статистику |

Закрытые суммы — только владельцу.

## Недостающие данные / решения владельца
1. **Окно изменений:** пилот до 22.11 (≤30 SKU, с контрольной группой) или только подготовка до середины января.
2. **Маржа и логистика (закрыто):** 4 семейства, особенно доставка 150PDS EQ3; доля возвратов; комиссии.
3. **MC-1:** 107817 и 107671 (в наличии); 5 OOS.
4. **Маршрут «levenhuk vegas ed 10x42»:** 26113 (по умолчанию) или 103640.
5. **Тексты:** подтверждение маркетинговых формулировок; гарантия, доставка, адрес шоурума — если нужны в объявлениях.
6. **CSV CS-Cart** по `cscart_export_spec.csv`; затем схема БД, если нужен SQL.

## Передача следующему участнику
- **Получатель:** ChatGPT.
- **Входные файлы и версия:** этот отзыв как `discussions/round-03/04_claude_review.md`; вложения `discussions/round-03/04_claude_attachments/`: `catalog_audit.py`, `catalog_buckets.csv`, `catalog_bucket_summary.csv`, `gemini_r3_crosswalk.csv`, `control_sku_variants.csv`, `shopping_query_routing_tests.csv`, `search_spec.py`, `search_keywords.csv`, `search_negatives.csv`, `search_rsa.csv`, `search_routing_results.csv`, `unit_economics_4sku.py`, `unit_economics_4sku.csv`, `cscart_export_spec.csv`, `carryover_round02_claude_review.md`. Базовый HEAD `7d10164`.
- **Задачи ChatGPT:**
  1. Перезапустить `catalog_audit.py` и `search_spec.py` (только файлы репозитория) и подтвердить результаты. Внести R3-CLAUDE-01…10 в `ISSUES.md`; закрыть R1-CHATGPT-04, R2-GEMINI-05; R3-CHATGPT-01/04 — по итогам проверки.
  2. Выполнить read-only E1–E3, E7, E10 (Merchant API) по 32 строкам `control_sku_variants.csv`; публично — только статусы и счётчики.
  3. Провести E11 (Ad Preview) по маршрутам Shopping и Search, записать расхождения с ожидаемыми результатами.
  4. Получить у владельца решения: окно сезона, MC-1, freeze как запрет записи, маршрут «vegas ed 10x42»; записать в `STATUS.md`.
  5. Решить судьбу `carryover_round02_claude_review.md` (исторический документ или вложение), удалить `claude_round01_upload.zip` из корня. Сформулировать задание на следующий шаг: пересчёт экономики на реальной марже и ТЗ скрипта наличия на Merchant API.
- **Ожидаемый результат:** `discussions/round-03/05_chatgpt_summary.md`, обновлённые `ISSUES.md` и `STATUS.md`, без объявления консенсуса по открытым блокерам.
- **Путь файла ответа:** `discussions/round-03/05_chatgpt_summary.md`

Claude Cowork не меняет рекламу, фиды и сайт и не объявляет консенсус.

**Источники (проверены 15.11.2026):**
- [Google Ads — Use campaign priority for Standard Shopping campaigns](https://support.google.com/google-ads/answer/6275296)
- [Google — Channel prioritization and budget allocation](https://blog.google/products/ads-commerce/channel-prioritization-budget-allocation/)
- [Google Ads — About negative keywords](https://support.google.com/google-ads/answer/12437241)
- [Google Ads — Keyword prioritisation](https://support.google.com/google-ads/answer/13389795)
- [Google Ads — About responsive search ads](https://support.google.com/google-ads/answer/7684791)
- [Google Ads API — shopping_product](https://developers.google.com/google-ads/api/fields/v17/shopping_product)
- [Google Ads Developer Blog — Merchant API is coming to Google Ads scripts](https://developers.google.com/ads/blog/posts/2026/04/merchant-api-is-coming-to-google-ads)
- [Content API for Shopping — deprecation and sunset](https://developers.google.com/shopping-content/guides/sunset)
- [Search Engine Land — Search terms report limits](https://searchengineland.com/google-ads-to-limit-search-terms-reporting-citing-privacy-340137)
