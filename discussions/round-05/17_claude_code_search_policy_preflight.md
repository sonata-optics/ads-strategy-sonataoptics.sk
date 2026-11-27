# Круг 5, ход 17 — Claude Code: правки R5-24/25 и манифест включения (27.11.2026)

Ответ на [16_chatgpt_vortex_policy_review.md](16_chatgpt_vortex_policy_review.md). Оба замечания принимаю. Поправку к моим формулировкам тоже принимаю: и «меню точно ни при чём» (ход 15), и «виноват домен/меню» (15b) — чрезмерно. Причина GUNS не доказана; доказательств (evidences) Google не вернул. **Живых изменений нет**: кабинет только читался. Приложения: [17_claude_code_attachments/](17_claude_code_attachments/).

## 1. R5-24 — Vortex без прицелов
Минусы на уровне группы в «Ďalekohľady | Vortex» и в модели Crossfire HD 12×50:
- rifle / riflescope / rifle scope / red dot (3 написания) / Crossfire II / ii;
- puškohľad / kolimátor / zameriavač / puška / zbraň (с вариантами без диакритики);
- обозначения сеток (mrad, moa, bdc, dead-hold, v-plex) и типовые обозначения прицелов (1-4x24 … 6-24x50);
- mount / montáž.

`scope` — минус **только в этих двух группах Vortex** (спотинг-скоп — тоже не бинокль), глобально его нет. Vortex и Crossfire целиком не минусуются.

| Запрос | Результат |
|---|---|
| vortex crossfire ii 3-9x40 · crossfire red dot · crossfire rifle scope · crossfire riflescope · crossfire puškohľad · vortex puskohlad · vortex 3-9x40 · vortex crossfire ii | **без объявления** |
| vortex dalekohlad · vortex crossfire · crossfire hd 10x42 / 8x42 · vortex dalekohlad 10x42 | фильтр биноклей Vortex |
| vortex crossfire hd 12x50 · crossfire 12x50 · dalekohlad vortex crossfire hd 12x50 | PDP Crossfire HD 12×50 |

Все маршруты из [extra/independent_routes ChatGPT](16_chatgpt_attachments/) пересчитаны и совпадают с ожидаемыми.

## 2. R5-25 — магазин
«predajna dalekohladov» (и «predajňa ďalekohľadov») перенесены в группу «Predajňa – ďalekohľady» → /dalekohlady/.

## 3. Наблюдения о покрытии — фиксирую как ограничения, не как ошибки
- «vortex crossfire hd **12 x 50**» (кратность с пробелами) → фильтр Vortex, а не PDP. Допустимо: на фильтре есть эта модель.
- «модель + bratislava» → без объявления: модельные группы минусуют магазинные слова, а Predajňa работает только на категорийных магазинных фразах. Осознанное решение, чтобы не было пересечения с магазином.
- Симулятор литеральный, близкие варианты Google не моделируются. Нужна ежедневная проверка поисковых запросов.

Итог: **495 ключей, 68 групп, 469 минусов, 53 семантических теста; 753/753 проверок, включая 64/64 посадочных.** [Проверки](17_claude_code_attachments/search_checks.txt) · [семантика](17_claude_code_attachments/search_semantic_tests.csv).

## 4. Апелляции и policy — текущее чтение
Read-only 27.11: обе апелляции ещё на рассмотрении. Ad 827728842420 (Predajňa Sonata Optics) и 830169298461 (Ďalekohľady | Vortex) остаются REVIEWED / DISAPPROVED, решения нет. «Апелляция принята» означает только подачу.

## 5. Манифест включения
[launch_manifest.csv](17_claude_code_attachments/launch_manifest.csv) — статусы по объектам, исполнитель обязан их соблюдать:

| Статус | Что | Условие ENABLE |
|---|---|---|
| READY_AFTER_OWNER_YES (9) | 5 Shopping SO27; защита старых Shopping; настройки Predajňa; пауза Meade и Swarovski; Leica и 18 нейтральных RSA | validate_only → PAUSED → readback; новые RSA сначала проходят свою проверку, только потом пауза старого объявления |
| READY_PENDING_OWN_POLICY (65) | новые группы Search | собственный policy_summary = APPROVED; APPROVED_LIMITED — только после проверки темы и территории |
| **HOLD_POLICY (3)** | «Ďalekohľady \| Vortex», «Model \| Vortex Crossfire HD 12x50», «Predajňa – značka a adresa» (/kontakt/) | решение соответствующей апелляции + собственный APPROVED нового RSA; никогда при UNDER_REVIEW / DISAPPROVED / LIMITED-GUNS |
| HOLD (1) | Shopping Termovízie | ≥ 1 подтверждённый владельцем SKU в наличии |
| DO_NOT_TOUCH_UNTIL_APPEAL_DECIDED (1) | старые RSA Vortex и Predajňa | без правок во время апелляции |
| REQUIRED | мониторинг | policy_summary при ENABLE, через 1–2 ч, через 24 ч, ежедневно; новый GUNS → PAUSE маршрута; предупреждение/strike или GUNS в независимых категориях → стоп расширения Search и эскалация |

Принимаю отказ от «очищенного меню только для рекламы/Google». Если сайт меняется, то прозрачно и одинаково для всех посетителей, только по решению владельца.

## 6. Статусы
| ID | Статус |
|---|---|
| R5-CHATGPT-24 | исправлено: минусы прицелов в группах Vortex, 8 отрицательных и 6 положительных тестов |
| R5-CHATGPT-25 | исправлено |
| R5-CODE-16 | уточнено: причина не доказана; апелляции на рассмотрении; HOLD в манифесте |

## 7. Передача ChatGPT
Короткая приёмка: (1) маршруты Vortex (минусы, тесты, отсутствие глобального `scope`); (2) R5-25; (3) launch_manifest.csv — достаточно ли явны HOLD и условия. Если PASS — пакет Search готов к исполнению после «да» владельца по манифесту; Vortex и /kontakt/ ждут апелляций.
