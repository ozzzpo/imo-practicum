# Данные кейса №2

Для проекта команда использует **Telco Customer Churn** от BlastChar, версия 1. Карточка Kaggle ссылается на IBM Sample Data Sets. [Карточка датасета](https://www.kaggle.com/datasets/blastchar/telco-customer-churn) · [Кейс №2](../context/case-02.md).

## Получение

После `uv sync` общий ноутбук сам получает данные при первом запуске:

```python
from src.data import load_raw

df = load_raw(download=True)
```

Если CSV отсутствует, загрузчик скачивает только файл
`WA_Fn-UseC_-Telco-Customer-Churn.csv` из **версии 1**
(`blastchar/telco-customer-churn/versions/1`) через `kagglehub`, проверяет
SHA-256 и сохраняет проверенный файл в `data/raw/`. Незавершённое скачивание
или файл с неверным хешем не сохраняются как рабочий CSV. При повторном
запуске используется локальный файл без обращения к Kaggle.

`load_raw()` без параметра `download=True` работает только с локальным файлом.
Для отдельного скачивания без чтения таблицы доступна функция `download_raw()`
из `src.data`. Существующий файл автоматически не заменяется: при неверном
хеше загрузчик останавливается с ошибкой.

Если Kaggle недоступен, можно скачать [ZIP версии 1](https://www.kaggle.com/api/v1/datasets/download/blastchar/telco-customer-churn?datasetVersionNumber=1)
и распаковать CSV в `data/raw/` вручную. Проверка хеша применяется и к ручной
загрузке. Подготовленные наборы храни в `data/processed/`. Обе папки
игнорируются Git.

Исходный CSV весит 977 501 байт. SHA-256 — `88be4b93fbe0cc83421af1c503794c97c342eca914c1576db7c276e61d61358a`. Функция `load_raw()` из [src/data.py](../src/data.py) сверяет хеш при каждой загрузке.

## Состав

Одна строка — один абонент. В файле 7 043 строки и 21 столбец. `Churn` показывает, ушёл ли абонент за последний месяц по определению набора. Значение `Yes` встречается 1 869 раз (26,5%), `No` — 5 174 раза. [Описание полей на Kaggle](https://www.kaggle.com/datasets/blastchar/telco-customer-churn).

| Группа | Поля |
|---|---|
| Идентификатор | `customerID` |
| Целевая переменная | `Churn` |
| Профиль абонента | `gender`, `SeniorCitizen`, `Partner`, `Dependents` |
| Услуги | `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `OnlineBackup`, `DeviceProtection`, `TechSupport`, `StreamingTV`, `StreamingMovies` |
| Договор и платежи | `tenure` (месяцы обслуживания), `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges` |

В исходнике 7 043 уникальных `customerID`. В `TotalCharges` есть 11 значений из пробельных символов, все при `tenure = 0`. Это исходные наблюдения для EDA. Платежи представлены способом оплаты и суммами, отдельных транзакций в CSV нет.
