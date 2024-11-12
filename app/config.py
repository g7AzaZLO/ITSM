import os

# Получаем директорию текущего файла (config.py)
CONFIG_DIR = os.path.dirname(os.path.abspath(__file__))

# Получаем базовую директорию проекта
BASE_DIR = os.path.dirname(CONFIG_DIR)

# Путь к файлу базы данных
DATABASE = os.path.join(BASE_DIR, "database", "database.db")