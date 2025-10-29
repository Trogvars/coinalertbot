# check_project.py - автоматический аудит проекта

import os
import ast
import re

def check_indentation(filepath):
    """Проверка отступов"""
    with open(filepath, 'r') as f:
        for i, line in enumerate(f, 1):
            if '\t' in line:
                print(f"❌ {filepath}:{i} - Используется Tab вместо пробелов")

def check_syntax(filepath):
    """Проверка синтаксиса Python"""
    try:
        with open(filepath, 'r') as f:
            ast.parse(f.read())
        print(f"✅ {filepath} - Синтаксис OK")
    except SyntaxError as e:
        print(f"❌ {filepath}:{e.lineno} - {e.msg}")

def check_imports(filepath):
    """Проверка неиспользуемых импортов"""
    # ... логика ...

# Сканируем весь проект
for root, dirs, files in os.walk('.'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            check_syntax(filepath)
            check_indentation(filepath)
