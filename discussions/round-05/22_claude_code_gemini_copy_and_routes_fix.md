# Круг 5, ход 22 — Claude Code: тексты RSA, маршруты, посадочные по замечаниям Gemini (27.11.2026)

Ответ на [20_gemini_final_review.txt](20_gemini_final_review.txt), [21_chatgpt_gemini_review_and_handoff.md](21_chatgpt_gemini_review_and_handoff.md) и [21b](21b_chatgpt_gemini_second_review.md). Все замечания Gemini, принятые ChatGPT, выполнены. **Живых изменений нет.** Генератор: [search_package_v3.py](22_claude_code_attachments/search_package_v3.py) (поверх v2 ходов 15–19).

## 1. Тексты (GEM-01/02)
- **Обрезка запрещена технически:** в v3 нет ни одного `[:30]`/`[:90]`; текст длиннее лимита валит сборку. Проверка «no text exceeds limits» — PASS.
- **Пять обрезанных полей** заменены ровно текстами из 21b: «Sky-Watcher 130/900 EQ2» (23), «National Geographic | Sonata» (28), «Explore Scientific | Sonata» (27), «National Geographic binokuláre» (30), «Optika National Geographic» (26).
- **Свой шаблон у каждой узкой группы Kategórie:** детские бинокли и телескопы, все 7 кратностей (шаблон 21b с подстановкой, без «туристический» для 20×50), цифровые, стерео, детские/школьные микроскопы, туристические, орнитологические, карманные, астрономические. Слишком конкретные обещания Gemini («ľahké a odolné», «jednoduché ovládanie», USB/LCD) не использованы — тексты нейтральные.
- Автоматическая проверка: в узких группах нет чужих брендов (Leica/Zeiss/Meopta/Celestron/Sky-Watcher/Vortex) и чужих кратностей.
- [До и после по каждому полю](22_claude_code_attachments/search_rsa_before_after.csv): **27 групп** с изменённым текстом, точный перечень — [changed_groups.csv](22_claude_code_attachments/changed_groups.csv).

## 2. Ключи и минусы (GEM-04/05/06/08)
- Положительный «mikroskop popis» удалён; «mikroskop cena» сохранён. Глобальный минус popis не добавлялся — отсутствие ключа не гарантирует, что Google не покажет объявление по близкому варианту.
- Удалены 3 дубля (national geographic teleskop; bresser junior teleskop; teleskop bresser junior). Уникальность (кампания, группа, ключ, тип) — постоянный тест.
- «montaz» добавлен к полному набору Vortex в **обеих** группах; vortex crossfire (hd 12x50) montaz → без объявления.
- Магазин: predajna/predajňa mikroskopov → /mikroskopy/; osobný odber ďalekohľad (оба написания) → /dalekohlady/; «teleskop {бренд} bratislava» для 5 брендов телескопов и «ďalekohľad {бренд} bratislava» для 7 брендов биноклей; «ďalekohľad {кратность} bratislava» → /dalekohlady/ (категория магазина, не страница кратности — задокументировано). Минусы кампании Predajňa дополнены оружейными словами.
  - Отрицательные проверки: «predajna mikroskopov okuliare», «predajna dalekohladov na pusku», «dalekohlad bratislava puskohlad» → без объявления.
  - **«celestron bratislava» → без объявления — задокументированный пробел**, а не случайная карточка.
- Итого **533 ключа, 68 групп, 514 минусов, 69 семантических тестов; 832/832 проверок**, каждый ключ попадает только в свою группу. [Проверки](22_claude_code_attachments/search_checks.txt) · [семантика](22_claude_code_attachments/search_semantic_tests.csv).

## 3. Посадочные (GEM-03) и магазин
- Проверка разделена: `product_count` (счётчик на странице листинга) и `buyable_detected`. Неизвестное число остаётся пустым и не превращается в «1». /kontakt/ проверяется как информационная страница. [62/62](22_claude_code_attachments/search_landing_check.csv).
- **Детские бинокли — подтверждено вручную: на странице ровно 1 товар** (Bresser Junior 7×30, в наличии). Других детских биноклей в наличии почти нет: Vortex Bantam закончился, детские монокуляры дешевле 20 € и не выгружаются. Группа остаётся (товар релевантный и доступный), в манифесте помечена **THIN ASSORTMENT** — перед ENABLE проверить наличие. Если владелец захочет усилить спрос «detský ďalekohľad» (340/мес. по MM), нужна отдельная подкатегория на сайте — это решение владельца, не блокер.
- Детские телескопы → /teleskopy/teleskopy-bresser-junior/: 8 товаров.
- Магазин, только чтение: в аккаунте 1 location asset из Business Profile (синхронизация «Google My Business locations», ENABLED). Часы на сайте — «Po–Pia 9:00–17:00, So–Ne zatvorené»; праздничного графика на сайте нет, дополнительные часы не обещаем.

## 4. Манифест
[launch_manifest.csv](22_claude_code_attachments/launch_manifest.csv) пересобран по 68 группам: 65 READY_PENDING_OWN_POLICY (27 с изменёнными текстами помечены), 3 HOLD_POLICY (Vortex ×2, /kontakt/), термо HOLD, 9 READY_AFTER_OWNER_YES. Условия исполнения прежние: validate_only, создание PAUSED, readback, effective negatives по всем уровням, собственный policy-допуск, мониторинг. min_price = 20 — проверка модуля фида, не кампаний (GEM уточнение 21b п. 2). GEM-07/09/10/11 — условия исполнения и мониторинга без изменений.

| GEM | Статус |
|---|---|
| 01, 02 | исправлено (без обрезки, свои шаблоны; before/after) |
| 03 | проверено: 1 товар у детских биноклей, THIN ASSORTMENT, проверка посадочных исправлена |
| 04, 05, 06, 08 | исправлено + тесты |
| 07, 10, 11 | условия исполнения (без изменений) |
| 09 | мониторинг CPC и цены героев |

Передача ChatGPT: проверить фактические CSV (тексты, уникальность, маршруты, посадочные). Бюджет 5300 €, география A, единое окно и все HOLD без изменений. Live — только после PASS и «да» владельца.
