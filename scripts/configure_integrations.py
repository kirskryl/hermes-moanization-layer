#!/usr/bin/env python3
"""Interactive, secret-free choice of optional integrations for a Hermes owner."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path


INTEGRATIONS = (
    ("google_workspace", "Google Drive, Docs и Sheets", "Подключить Google Drive, Docs и Sheets?", "Укажите разрешённые папки или документы и режим: чтение либо правки."),
    ("mail", "Почта", "Подключить почту?", "Укажите сервис, адрес учётной записи и разрешённые действия: чтение, черновики, отправка."),
    ("calendar", "Календарь и напоминания", "Подключить календарь и напоминания?", "Укажите сервис, календари, часовой пояс и можно ли создавать или менять события."),
    ("notes", "Личные заметки", "Подключить заметки?", "Укажите разрешённые папки и папки, которые нужно исключить."),
    ("computer", "Локальный компьютер", "Подключить коннектор к компьютеру?", "Укажите разрешённые папки и действия: поиск, чтение, создание, редактирование, отправка файлов."),
    ("telegram_channel", "Telegram-канал", "Подключить свой Telegram-канал?", "Укажите @канал или ссылку и разрешения: анализ, черновики, публикация."),
    ("telethon", "Личный Telegram", "Подключить личный Telegram через Telethon?", "Укажите разрешённые чаты и действия. Сессия создаётся только на устройстве владельца."),
    ("public_sources", "Сайт и публичные материалы", "Добавить сайт или другие публичные источники знаний?", "Укажите сайт, канал, базу знаний или публичные документы."),
    ("crm", "CRM и клиентская база", "Подключить CRM?", "Укажите систему, разрешённые сущности и режим: чтение, черновики, изменения после подтверждения."),
    ("getcourse", "GetCourse", "Подключить GetCourse?", "Укажите домен школы, разрешённые разделы и режим: чтение, черновики, изменения после подтверждения."),
    ("bots", "Собственные боты", "Подключить собственных ботов?", "Укажите назначение каждого бота и разрешённые действия. Один токен обслуживает один polling-процесс."),
    ("content", "Контентные навыки", "Подключить контентные навыки?", "Выберите нужное: аналитика канала, посты, сценарии, монтаж, публикация."),
    ("meetings", "Zoom и SumKit", "Подключить записи встреч, расшифровку и саммари?", "Укажите сервисы и разрешённые папки для материалов."),
    ("browser", "Браузерные задачи", "Подключить браузерные задачи, включая сервисы вроде Авито?", "Укажите сайты и разрешённые действия. Исходящие действия подтверждаются владельцем."),
    ("server", "Серверный режим", "Разрешить работу с вашими проектами и сервером?", "Укажите репозитории, хосты и режим: диагностика, правки с подтверждением, автоматический деплой."),
    ("payments", "Платёжный режим", "Подключить платёжный режим?", "Укажите, какие операции допустимы, лимиты и правило подтверждения. Режим остаётся выключенным до отдельной настройки."),
)


def yes_no(question: str) -> bool:
    while True:
        answer = input(f"{question} [y/N] ").strip().lower()
        if answer in {"", "n", "no", "нет", "н"}:
            return False
        if answer in {"y", "yes", "да", "д"}:
            return True
        print("Ответьте «да» или «нет».")


def previous_choices(output: Path) -> dict[str, tuple[str, str]]:
    if not output.is_file():
        return {}
    found: dict[str, tuple[str, str]] = {}
    pattern = re.compile(
        r"^## (?P<title>.+?)\n- id: `(?P<key>[a-z_]+)`\n- статус: выбрано для подключения\n"
        r"- параметры владельца: (?P<note>.*)$",
        re.MULTILINE,
    )
    for match in pattern.finditer(output.read_text(encoding="utf-8")):
        note = safe_note(match.group("note"), announce=False)
        found[match.group("key")] = (match.group("title"), note)
    return found


def safe_note(note: str, *, announce: bool = True) -> str:
    markers = re.compile(r"(?i)(password|secret|token|api[_-]?key|cookie|bearer|authorization|код\s*2fa|otp|парол[ья]?|токен|секрет|ключ)")
    opaque_value = re.compile(r"[A-Za-z0-9_-]{24,}")
    if len(note) > 500 or "\n" in note or "\r" in note or markers.search(note) or opaque_value.search(note):
        if announce:
            print("Комментарий похож на секрет или слишком длинный и не будет сохранён.")
        return ""
    return note


def write_plan(output: Path, rows: list[tuple[str, str, str]]) -> None:
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    body = [
        "# Добровольные интеграции",
        "",
        "Этот файл хранится только у владельца. В нём нет паролей, токенов, cookie, ключей и кодов 2FA.",
        "Подключайте отмеченные пункты по одному штатным OAuth или подтверждённым способом, затем проверяйте результат.",
        "",
    ]
    for key, title, note in rows:
        body.extend((f"## {title}", f"- id: `{key}`", "- статус: выбрано для подключения", f"- параметры владельца: {note or 'не указаны'}", ""))
    tmp = output.with_suffix(output.suffix + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        stream.write("\n".join(body))
    os.replace(tmp, output)
    os.chmod(output, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print("\nНастройка добровольных интеграций. Пароли, токены, cookie, ключи и коды 2FA сюда не вводятся.")
    selected = previous_choices(args.output)
    if selected:
        print("Ранее выбранные пункты будут сохранены; «да» обновляет комментарий выбранной интеграции.")
    for key, title, question, hint in INTEGRATIONS:
        if not yes_no(question):
            continue
        note = input(f"{hint}\nКомментарий можно оставить пустым: ").strip()
        selected[key] = (title, safe_note(note))
    rows = [(key, title, note) for key, (title, note) in selected.items()]
    write_plan(args.output, rows)
    print(f"\nСохранён локальный план: {args.output}")
    if rows:
        print("Откройте его в первом диалоге с агентом: он проведёт подключение и проверку по одному пункту.")
    else:
        print("Интеграции пропущены. Их можно выбрать позже, повторно запустив этот скрипт.")


if __name__ == "__main__":
    main()
