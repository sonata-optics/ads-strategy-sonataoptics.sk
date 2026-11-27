# Дополнение 21b — второй ответ Gemini: решения и тексты для Code22
ChatGPT, 27.11.2026. Вход репозитория c94d020e5cee66f0565857cb73a6efa45bc0d1f5. Источник: второй ответ Gemini, полностью переданный владельцем в чат. Ниже авторский разбор/конспект, не дословная копия. Gemini подтвердил чтение компактного файла до END_GEMINI_REPEAT_2026_11_27 и оценивал решения хода21, НЕ исполненный пакет22. Code22 на момент проверки ещё не опубликован.

## Итог
Принять согласование GEM-FINAL-01…11 и конкретизацию текстов/тестов. Новых стратегических разногласий нет. Следующий ход остаётся **Claude Code22**, затем короткая проверка фактических CSV. Не объявлять замечания закрытыми по согласованию намерений. Shopping PASS и прежние runtime gates сохраняются; 3 HOLD_POLICY и thermal HOLD отдельно. T5300, единое окно и география A без изменений. Разрешения на live нет.

## Что Gemini подтвердил
- 01/02: обрезки и несоответствие шаблонов исправить до ENABLE затронутых RSA.
- 03: он принял, что products_or_buyable=1 не доказывает один товар; нужна фактическая проверка.
- 04/05/06: удалить положительный mikroskop popis, добавить montaz в обе Vortex-группы, удалить три дубля и добавить проверки уникальности.
- 07/10/11: effective negatives, validate_only/readback бюджета и tracking остаются условиями исполнения/экономических выводов, не новым спором о стратегии.
- 08: магазин уже содержит PHRASE; добавляются конкретные недостающие маршруты.
- 09: CPC дешёвого hero — мониторинговое наблюдение, не новый блокер.
Новых обязательных вопросов владельцу нет.

## Пять коротких заголовков — принять для реализации
| Группа / поле | Текст | Символов |
|---|---|---:|
| Model Sky-Watcher Explorer 130/900 EQ2 H1 | Sky-Watcher 130/900 EQ2 | 23 |
| Teleskopy National Geographic H2 | National Geographic \| Sonata | 28 |
| Teleskopy Explore Scientific H2 | Explore Scientific \| Sonata | 27 |
| Ďalekohľady National Geographic H1 | National Geographic binokuláre | 30 |
| Ďalekohľady National Geographic H2 | Optika National Geographic | 26 |

Длины пересчитаны ChatGPT. Первые варианты H2 с перестановкой «бренд + teleskopy» заменены на варианты выше, чтобы не повторять H1. Это редакционная избыточность внутри RSA, а не доказанная «каннибализация» аукциона. Проверять также уникальность всех H в итоговой группе.

## Компактные шаблоны Gemini — принять с проверкой заявлений
Следующие тексты — редакционные кандидаты, не внедрённые объявления. Code сверяет весь набор с фактической посадочной, длины считает программно после подстановок.

**Detské ďalekohľady**
H: Detské ďalekohľady; Ďalekohľady pre deti; Ďalekohľad ako darček; Poradíme s výberom | Sonata.
D1: Detské ďalekohľady na prírodu a výlety. Pomôžeme vybrať model podľa veku dieťaťa.
D2: Predajňa v Bratislave a doprava po celom Slovensku. Odborné poradenstvo pred nákupom.
**Поправка:** предложенное Gemini «Ľahké a odolné pre deti» не использовать универсально без подтверждения веса/прочности представленных моделей. Оно не требуется для числа заголовков.

**Teleskopy pre deti**
H: Teleskopy pre deti; Detské hvezdárske ďalekohľady; Prvý teleskop na hviezdy; Teleskop pre deti ako darček; Poradíme s výberom | Sonata.
D1: Teleskopy pre deti a začiatočníkov na prvé pozorovanie Mesiaca a hviezd. Poradíme.
D2 (нейтральная замена): Predajňa v Bratislave, doprava po Slovensku. Pomôžeme s výberom teleskopu.
**Поправка:** «Jednoduché ovládanie vhodné pre deti» не обещать всем моделям автоматически; учитывать возраст и помощь взрослого.

**Кратность {X}x{Y}**
H: Ďalekohľady {X}x{Y}; Binokuláre {X}x{Y} | Sonata; Výber modelov {X}x{Y}; Poradíme s výberom optiky; Predajňa v Bratislave.
D1 (нейтральный вариант для всех кратностей): Ďalekohľady {X}x{Y}. Pomôžeme vybrať model podľa spôsobu pozorovania.
D2: Aktuálna ponuka ďalekohľadov {X}x{Y}. Predajňa v Bratislave a doprava po Slovensku.
**Поправка:** не называть каждую кратность туристической автоматически, особенно 20x50. Длины после подстановки, никаких чужих кратностей.

**Digitálne mikroskopy**
H: Digitálne mikroskopy; USB a LCD mikroskopy; Mikroskopy s kamerou; Odborné poradenstvo | Sonata; Predajňa v Bratislave.
D1: Digitálne mikroskopy s pripojením k PC alebo s displejom. Pomôžeme vybrať správny model.
D2: Pre dielňu, laboratórium aj kontrolu detailov. Predajňa v Bratislave, doprava po SR.
USB/LCD, подключение к PC/дисплей и назначения оставлять только при подтверждённом ассортименте соответствующей посадочной; при отсутствии подтверждения нейтрально «Digitálne mikroskopy. Pomôžeme vybrať model podľa vašich požiadaviek.»

**Stereomikroskopy**
H: Stereomikroskopy; Stereoskopické mikroskopy; 3D obraz pre dielňu a servis; Odborné poradenstvo | Sonata; Predajňa v Bratislave.
D1: Stereoskopické mikroskopy pre servis, elektroniku, laboratóriá aj hobby. Poradíme.
D2: Priestorový 3D obraz a pracovná vzdialenosť. Predajňa v Bratislave, doprava po SR.
Сверить назначения с реальными моделями. Для более ясного D2 допустимо: «Pomôžeme vybrať stereomikroskop na vašu prácu. Predajňa v Bratislave.»

## Сценарии Gemini для Code22
| Запрос | Ожидаемый результат |
|---|---|
| vortex crossfire montaz | no ad |
| vortex crossfire hd 12x50 montaz | no ad |
| vortex crossfire hd 12x50 | модель Vortex → PDP 12x50; policy HOLD всё ещё действует |
| mikroskop popis | нет литерального маршрута после удаления положительного ключа |
| mikroskop cena | Mikroskopy → /mikroskopy/ |
| predajna mikroskopov / predajňa mikroskopov | Predajňa mikroskopy → /mikroskopy/ |
| osobny odber dalekohlad / osobný odber ďalekohľad | Predajňa ďalekohľady → /dalekohlady/ |
| teleskop celestron bratislava | Predajňa teleskopy → /teleskopy/ |
| dalekohlad 10x42 bratislava | магазин биноклей → согласованная категория или точная 10x42; маршрут задокументировать |
| predajna mikroskopov okuliare | no ad |
| predajna dalekohladov na pusku | no ad |
| celestron bratislava | пока no ad — явно документированный пробел, не случайная PDP |

ChatGPT независимо подтвердил на локальном пакете19: после удаления positive mikroskop popis литеральный маршрут пуст, а mikroskop cena сохранён. **Это не гарантия отсутствия будущего реального показа Google по информационной фразе**: удалить положительный ключ и исключить запрос — разные действия. Глобальный popis не добавлять; при необходимости отдельного исключения обсуждать узкий exact после фактов search terms.
У новых магазинных фраз нужны не только положительные, но и отрицательные проверки; Vortex group negatives не защищают Predajňa автоматически.

## Уточнения к приёмке и передаче
1. Числа Gemini «16–19 исправляемых / 45–49 готовых» приблизительны. Code отдаёт **точный перечень уникальных групп**, без двойного счёта пересечений (Vortex/шаблоны/новые фразы). Не использовать приблизительные числа для ENABLE.
2. google.min_price=20 — конфигурация выгрузки каталога, не поле четырёх Ads-кампаний. Readback label4 scope выполняется для каждой из четырёх; ценовой порог проверяется в модуле/фиде отдельно. При снижении порога — прежнее стоп-условие.
3. Наличие поддержанного total budget в документации не заменяет validate_only и чтение фактических дат/суммы/валюты.
4. Собственный policy-допуск и положительное разрешение причины апелляции нужны независимо от технических тестов; не снимать HOLD по этому согласованию.
5. AdsGate и rollback не получили дополнительной проверки Gemini, но ранее выполненная техническая приёмка не аннулируется его неполным первым контекстом.

**Задание Code22:** выполнить ход21 + это дополнение, регенерировать CSV/manifest, приложить before/after RSA и результаты уникальности/длин/семантики. Остальные поля стратегии не менять. Затем ChatGPT проверяет фактический результат; нового круга общих рассуждений Gemini не требуется. Live только после предусмотренного PASS и явного «да» владельца.
