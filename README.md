# Qemployees. Hierarchical acquisition project
**Задача:** Необходимо импортировать данные по организациям и пользователям в SQL таблицу из
приложенного к заданию json файла. У компании есть офисы (type = 1) в нескольких городах, в каждом из них есть отделы (type = 2),
где работают сотрудники (type = 3). Необходимо реализовать выборку всех сотрудников по
указанному идентификатору сотрудника.

## Пререквизиты
1. [`poetry`](https://python-poetry.org/docs/#installation) tool for dependency management and packaging;
2. `python >= 3.10`;
3. [PostgreSQL](https://postgrespro.ru/windows) дистрибутив или [`docker`](https://www.docker.com) вместе с `docker compose`.

## Инструкция к использованию
1. Установить необходимые зависимости с помощью `poetry install`;
2. Создать `.env` файл и наполнить переменными из `.env.dist`;
3. Запустить контейнер с СУБД `docker-compose up`;
4. Создать таблицу в БД с помощью `poetry run qemployees service -i`;
5. Наполнить таблицу тестовыми данными `poetry run qemployees service -ld fixtures/input_test.json`;
6. Запустить поиск по ID с помощью `poetry run qemployees query {ID}`.

Справка по модулю и командам доступна через `poetry run qemployees {service, query} -h`

## Описание решения
CLI приложение с двумя режимами: сервисный, для управления таблицей и данными в ней; "боевой", для выполнения бизнес-логики по поиску сотрудников. Адрес БД, структуру файла с фикстурами и экстремумы уровней вложенности можно менять с помощью соответствующих переменных среды.

Поиск всех "соседей" нижнего уровня внутри сущности верхнего уровня осуществляется с помощью рекурсивного запроса следующего вида:
```SQL
WITH RECURSIVE path AS (
    SELECT h.id, h.parent_id, h.name, h.type
    FROM hier h
    WHERE h.id = $1
    UNION ALL
    SELECT h.id, h.parent_id, h.name, h.type
    FROM hier h
    JOIN path p ON p.parent_id = h.id
),
top AS (
    SELECT p.id
    FROM path p
    WHERE p.type = $2
),
children AS (
    SELECT h.id, h.parent_id, h.name, h.type
    FROM hier h
    WHERE h.id = (SELECT t.id FROM top t)
    UNION ALL
    SELECT h.id, h.parent_id, h.name, h.type
    FROM hier h
    JOIN children c ON c.id = h.parent_id
)
SELECT c.id, c.parent_id, c.name, c.type
FROM children c
WHERE c.type = $3
```
Где `$1 = {ID}, $2 = {TOP_LEVEL}, $3 = {BOTTOM_LEVEL}`. Сначала рекурсивно строится путь от нужного сотрудника до самого верхнего уровня, потом определяется идентификатор этого предка, а затем строится выборка всех потомков этого предка до самого нижнего уровня, в итоге результат фильтруется по значению `h.type`.

План запроса на данных из тестовой [фикстуры](fixtures/input_test.json) можно посмотреть по [ссылке](https://explain.tensor.ru/archive/explain/4565f124d25a14c95d1c92d7b041012f:0:2025-01-24). Из проблем можно отметить три `Seq Scan` и занижение ожидаемого количества строк. Индексы не используются.

## Перспективы оптимизации
Данная в задании тестовая выборка слишком мала для построения оптимального плана, поэтому для тестов были сгенерированы случайные выборки с равномерным распределением, отличающиеся общим объемом по уровням вложенности (`type=1:type=2:type=3`).

Учитывая план исходного запроса можно предположить, что создание индекса на `parent_id` увеличит производительность. Однако, такой индекс не используется на выборке, например в 2000 сотрудников (`10:50:2000`, [план](https://explain.tensor.ru/archive/explain/dbc4c74828bf63716f502b612ff7475f:0:2025-01-24)). Спустя несколько попыток дальнейшего увеличения объема выборки был получен `Bitmap Index Scan` в одном из узлов `CTE children`, что уменьшило время выполнения в 10 раз по сравнению с таким же запросом над таблицей без индекса.

В зависимости от контекста использования, можно предположить и другие варианты оптимизации. Какое-то время можно выиграть на этапе планирования за счет подготовленного оператора (`PREPARE`), если мы можем поддерживать сеанс. 

В зависимости от частоты изменений содержания таблицы можно хранить данные в денормализованном виде и вычислять заранее `root_id` (идентификатор связанной сущности верхнего уровня) для каждой строки.

Возможно стоит попробовать хранить данные в другой структуре, например `Nested Sets` или `Closure Table`, что опять же зависит от частоты изменения данных. 

Кроме того, можно переписать логику приложения в асинхронном коде.