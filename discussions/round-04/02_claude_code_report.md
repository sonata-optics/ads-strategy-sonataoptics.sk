# Claude Code — технический пакет круга 4
Автор: Claude Code (исполнитель, не участник стратегического голосования). Круг 4, 15.11.2026.
Задание: [01b_task_to_claude_code.md](01b_task_to_claude_code.md). **Входной SHA: `677a7a3bda75303b213522ba60fa4b63ce994100`.**
Прочитано: README.md, PROTOCOL.md, discussions/STATUS.md, ISSUES.md, round-03/04_claude_review.md, round-03/05_chatgpt_summary.md, все файлы round-03/04_claude_attachments/ (использованы control_sku_variants.csv, search_*.csv, search_spec.py, unit_economics_4sku.*, shopping_query_routing_tests.csv), round-03/05_chatgpt_attachments/live_checks_2026-11-15.json, markets/sk/05_budget_and_roas.md и 06_model_query_visibility.md, data/catalog/2026-11-14 (merchant-*, assortment-*). Ответа Gemini в round-04 нет; эта работа не является отзывом Gemini.

**Живые Ads/Merchant/сайт не менялись, бюджет не расходовался.** Использованы только read-only запросы Google Ads API (GAQL) 15.11.2026; финансовые данные не выгружались и не публикуются.

## Резюме
1. Все пять результатов выполнены кодом; [run_all.py](02_claude_code_attachments/run_all.py) прогоняет скрипты и 28 проверок пакета — **все PASS** ([вывод](02_claude_code_attachments/test_run_output.txt)).
2. Карта покрытия: 32 строки = 26 уникальных offerId + 6 site-only. 21 ELIGIBLE, 3 OOS, **26130 — IN_STOCK без кампании**, 26131 — OOS без кампании, 6 site-only — статус неизвестен.
3. **Новый ФАКТ:** три Shopping-кампании без campaign scope (`24341660055`, `24346760069`, `24346760072`) не рекламируют ни один из 26 ID; у `24341660055` Google возвращает «excluded listing group» и **«campaign ended»**. Статус ENABLED в E1 не равен работающей кампании.
4. **Главный блокер семантики:** account-level BROAD `kde` блокирует «kde kúpiť + модель» и в Search, и в Shopping (R07–R09). Аналогично `aký`, `stary`, `lacno`, `heureka`, `Ktoré`. В account list также есть мусорная запись `keyword_text`.
5. 47 тестов маршрутов: 27 PASS, 13 FAIL, 4 работают только при допущении close variants, 2 риска, 1 решение владельца. Симуляция предложенного diff оставляет 3 FAIL — все три решения владельца.
6. Экономика Cowork воспроизведена бит-в-бит; независимая формула совпала (≤0,005 €); 14/14 граничных тестов.
7. Stock sync: спецификация + локальная модель, 16/16 сценариев, включая запрет авто-включения ручной паузы и REVIEW-групп.

## Как запустить
```bash
python -I discussions/round-04/02_claude_code_attachments/run_all.py
```
Без сети, только файлы репозитория (read-only выгрузки 15.11 лежат в `02_claude_code_attachments/inputs/`). Python 3.12, только стандартная библиотека. Отдельно: `coverage_map.py`, `routing_tests.py`, `economics_recheck.py`, `stock_sync_dryrun.py`.

## Файлы
| Файл | Что внутри |
| --- | --- |
| [coverage_map.csv](02_claude_code_attachments/coverage_map.csv) / [.py](02_claude_code_attachments/coverage_map.py) | 32 строки; факты 14.11 и 15.11 в отдельных колонках с датой; статус, причина, текущий campaign/filter, проектная группа, приёмка до/после запуска, откат и его граница |
| [routing_tests.csv](02_claude_code_attachments/routing_tests.csv) / [routing_tests.py](02_claude_code_attachments/routing_tests.py) | 47 запросов; account 258 + campaign 95 + ad group 0 негативов; литеральная модель отдельно от гипотезы close variants |
| [routing_tests_after_proposed_diff.csv](02_claude_code_attachments/routing_tests_after_proposed_diff.csv) | Симуляция diff (ничего не применено) |
| [negative_keyword_diff.csv](02_claude_code_attachments/negative_keyword_diff.csv) | 16 предложений: основание, пример-тест, риск, проверка; статус PROPOSAL_NOT_APPLIED |
| [migration_checklist.md](02_claude_code_attachments/migration_checklist.md) | Пилот priority=1, allowlist 26 item_id, статические проверки, доставка после запуска, откат, граница 26130 |
| [stock_sync_spec.md](02_claude_code_attachments/stock_sync_spec.md), [stock_sync_dryrun.py](02_claude_code_attachments/stock_sync_dryrun.py) | Спецификация и dry-run модель; журнал и результаты сценариев |
| [economics_recheck.py](02_claude_code_attachments/economics_recheck.py), [economics_recheck.csv](02_claude_code_attachments/economics_recheck.csv), [economics_edge_tests.csv](02_claude_code_attachments/economics_edge_tests.csv) | Повтор Cowork + независимая формула + граничные тесты |
| [inputs/](02_claude_code_attachments/inputs/live_recheck_2026-11-15_claude_code.json) | Read-only сверка 15.11 (shopping_product по 8 кампаниям, 95 campaign negatives) |
| [test_run_output.txt](02_claude_code_attachments/test_run_output.txt) | Полный вывод последнего прогона |

## 1. Карта покрытия (R3-CHATGPT-06)
| Статус | Строк | Пример |
| --- | ---: | --- |
| COVERED_ELIGIBLE | 21 | 103933, 26113, 103640 в `24440851881`; 47420 в `24451885423` |
| NOT_ELIGIBLE_OOS | 3 | 47424, 47412, 47458 — в scope, OOS правдиво |
| GAP_IN_STOCK_NO_CAMPAIGN | 1 | **26130** монокуляр, label `monokuláre` |
| GAP_OOS_AND_NO_CAMPAIGN | 1 | 26131 — даже при возврате наличия не будет рекламироваться |
| SITE_ONLY_UNKNOWN | 6 | URL в sitemap 14.11, но не в Merchant-снимке; текущее состояние не проверялось |

ФАКТ: каждый ID проверен во всех 8 ENABLED Shopping-кампаниях (14 + 10 + 3×26 строк). Объединение хранит все campaign-строки ID (колонка `fact_cc_2026_11_15_campaigns`), есть отдельный unit-тест на дубликаты. 26130 в проекте маршрутизируется по item_id, label остаётся `monokuláre`. UNKNOWN не заменён историческими значениями.

## 2. Маршруты и минус-слова (R3-CHATGPT-07)
Литеральная модель: регистр не важен (документировано Google), диакритика/дефисы/× сохраняются; негативы не расширяются на close variants (документировано Google). Гипотеза CV — отдельная колонка, используется только для позитивных ключей.

| Группа тестов | Итог | Причина |
| --- | --- | --- |
| 4 модели + 3 запроса владельца | R01, R02, R05, R06 PASS; **R03 (×) и R04 (дефис) — CV_DEPENDENT** | Ключи Cowork нормализованы; запрос владельца в исходном написании совпадает только при close variants |
| kde kúpiť + модель | **FAIL ×3** | account BROAD `kde`; блокирует и Shopping |
| cena | PASS ×3; `lacno` FAIL | account BROAD `lacno` |
| New / old / без ED | R14 решение владельца; **R16 «nový» FAIL**; R17 `stary` FAIL, R18 `starý` проходит | Несогласованность: негатив без диакритики не ловит форму с диакритикой |
| Монокуляр/бинокль, кратность, GoTo | PASS (Search не маршрутизирует в чужую группу) | Shopping по 26130 сегодня невозможен — нет кампании |
| Аксессуары | **R31–R33 FAIL** (ложноположительные) | phrase «trinovid 10x42», «150pds eq3» ловят «puzdro», «popruh», «okulár» |
| Исключаемые | R44 «návod pdf» FAIL | negatives návod/manual есть только в старых Search-кампаниях и не наследуются новыми |

[Diff](02_claude_code_attachments/negative_keyword_diff.csv) — только предложения: заменить `kde`, `stary`, `aký` узкими PHRASE после выгрузки search terms за 90 дней; удалить `keyword_text`; добавить `bazár` на уровень аккаунта; ключи в форме владельца (дефис, «10 x 42», «nový»); accessory-негативы в группах; копировать návod/manual/pdf в новые кампании. `lacno`, `heureka`, `Ktoré` — решение владельца.

## 3. Миграция (R3-CHATGPT-09)
[Чек-лист](02_claude_code_attachments/migration_checklist.md): новая кампания PAUSED, priority 1 при текущих 0; allowlist 26 item_id, everything else EXCLUDED; старые scopes в этом шаге не меняются. До запуска — только статические проверки (`shopping_product` по пилоту, обход дерева, негативы). После разрешённого запуска — фактическая доставка по `shopping_performance_view`. Исключение из старых кампаний — отдельное решение по доказательствам, не по таймеру 48–72 ч. Откат восстанавливает настройки, но не гарантирует показ; **для 26130 откат = возврат к нулевому покрытию**.

## 4. Stock sync (R3-CHATGPT-10)
[Спецификация](02_claude_code_attachments/stock_sync_spec.md). Управляет только Search-группами allowlist; Shopping не трогает. Составная identity `merchant~channel~lang~feed_label~offer_id`. Ошибка API, пустой ответ, устаревшее чтение, отсутствие товара → никаких действий. Ручная пауза и REVIEW-группа никогда не включаются. Повторное включение — после двух свежих чтений IN_STOCK. Массовый flip > 30 % → HALT. Идемпотентность и журнал проверены.

## 5. Экономика (повтор Cowork, R3-CHATGPT-08 частично)
- `unit_economics_4sku.py` перезапущен: 24 строки идентичны опубликованному CSV.
- Независимая реализация формулы из 05_budget_and_roas.md: максимальное отличие CM 0,005 € (округление).
- Граничные тесты: нулевая и отрицательная маржа (порогов нет, Max CPC = 0), r=1, монотонность по r, **смешивание баз value меняет вывод** (E07), CPA на оставшуюся покупку, desired_profit ≥ CM, CR покупки/клики vs покупки/сессии, неизвестные клики = UNKNOWN, 0 покупок = недостаточно данных, частичные возвраты по состояниям ≠ усреднённый r.
- Маржа безубыточности в сценарии Cowork: 3,5 % (103933) … 8,9 % (47420). Это свойство сценарных затрат, не реальная маржа.
- Порог 74 показов не использован ни как мощность, ни как автооткат. Вопрос остаётся у Cowork.

## Критика и риски
| ID | Тезис | Риск | Доказательство | Исправление / проверка |
| --- | --- | --- | --- | --- |
| R4-CLAUDECODE-01 | Account list блокирует коммерческие модельные запросы | «kde kúpiť …», «aký …», «… stary model» не дают ни Search, ни Shopping | routing_tests R07–R09, R17, R40 | Search terms за 90 дней → решение владельца по diff; повтор теста |
| R4-CLAUDECODE-02 | Три старые Shopping-кампании без scope фактически не рекламируют 26 ID | Покрытие каталога могло считаться шире фактического; хвост каталога может опираться на завершённые кампании | `shopping_product` по 24341660055 (excluded + campaign_ended); 2 других — причина не получена | Выгрузить end_date и деревья всех 8 кампаний (E1/E2) до плана полного масштаба |
| R4-CLAUDECODE-03 | Тесты Cowork r3 нормализовали написание до сравнения | 24/24 PASS переоценивали готовность: × и дефис владельца проходят только при close variants | R03, R04, R35, R38 | Ключи в исходной форме; после запуска — search_term_view |
| R4-CLAUDECODE-04 | Phrase-ключи ловят аксессуары | Клики «puzdro/okulár» на дорогую модель | R31–R33 | Accessory-негативы групп |
| R4-CLAUDECODE-05 | Новые кампании не наследуют campaign negatives старых | návod/manual/pdf/puškohľad пройдут в пилот | R44; campaign_negatives_2026-11-15.csv | Явно перенести нужные PHRASE в новые кампании |
| R4-CLAUDECODE-06 | Отклонение от Cowork: в allowlist 26 ID, а не 22 | OOS-товары в пилоте без показов, «пустые» группы | coverage_map | Cowork подтверждает или возвращает 22; тогда нужен механизм добавления при возврате наличия |

## Ответ на открытые ID
| ID | Статус от Claude Code | Доказательство |
| --- | --- | --- |
| R3-CHATGPT-06 | исправлено в проекте, ждёт проверки Cowork | coverage_map: 26130 в allowlist, label не меняется, граница отката |
| R3-CHATGPT-07 | исправлено в тестах; diff ждёт решения владельца | routing_tests + diff + симуляция |
| R3-CHATGPT-08 | не решается кодом; передано Cowork | экономика повторена; 74 не используется |
| R3-CHATGPT-09 | исправлено в чек-листе, ждёт проверки | migration_checklist §2–§6 |
| R3-CHATGPT-10 | исправлено в спецификации и модели, ждёт проверки | stock_sync 16/16 |

## Ограничения (НЕТ ДАННЫХ)
- E1: бюджеты, гео, расписание, end dates (кроме причины `campaign_ended` у 24341660055).
- E10: GTIN/MPN, destination statuses — не запрашивались; их отсутствие в выгрузке не означает отсутствия в Merchant.
- E11: Ad Preview не выполнялся; фактическая доставка не проверялась — пилот не существует.
- Состояние 6 site-only URL в текущем Merchant/CS-Cart не проверено.
- Причины NOT_ELIGIBLE в `24346760069`/`24346760072` не получены.
- Search terms за прошлые периоды (основание для удаления `kde` и др.) — закрытые данные, не выгружались.
- Close variants Google не симулируются; колонка CV — гипотеза.

## Что требует решения владельца
`kde`, `aký`, `stary`, `lacno`, `heureka`, `Ktoré`; поведение запроса без ED (R3-CLAUDE-09); состав пилота 22 vs 26; бюджет/ставки/окно запуска; судьба завершённых кампаний без scope; источник истины для stock sync.

## Передача — Claude Cowork
По заданию [01c_task_to_cowork.md](01c_task_to_cowork.md). Ответ: `discussions/round-04/03_claude_review.md`, приложения `03_claude_attachments/`.
1. Пересчитать экономику независимо (с возвратами, обе базы value, отрицательный вклад, CR покупки/клики, пределы CPC); проверить [economics_edge_tests.csv](02_claude_code_attachments/economics_edge_tests.csv) и составить список недостающих закрытых данных.
2. Проверить [coverage_map.csv](02_claude_code_attachments/coverage_map.csv): 32/26/6, 26130, хвост каталога, R4-CLAUDECODE-02, решение 22 vs 26 (R4-CLAUDECODE-06).
3. Переработать оценку 74 показов: модель, baseline, дисперсия, мощность, сезонность, повторные проверки; разделить технический стоп, предел расходов и коммерческое решение с лагом.
4. Проверить тесты [routing_tests.csv](02_claude_code_attachments/routing_tests.csv) и контрпримеры; дать статус R3-CHATGPT-06…10 и R4-CLAUDECODE-01…06.
5. Проверить, что [stock_sync_spec.md](02_claude_code_attachments/stock_sync_spec.md) не включает ручную/REVIEW паузу и не трактует пустой ответ как OOS.
Live изменения этим заданием запрещены. После Cowork — ChatGPT (сводка) → Gemini (Google-рецензия текстом).
