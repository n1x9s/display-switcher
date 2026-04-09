# Display Switcher

Автоматически переключает основной дисплей на macOS, когда наклоняешь крышку MacBook.

**Крышка ниже порога** → внешний монитор становится основным, яркость встроенного экрана обнуляется, Dock переезжает.
**Крышка выше порога** → MacBook становится основным, яркость восстанавливается, Dock возвращается.

На маках без датчика угла крышки работает fallback по яркости экрана.

## Совместимость

**Датчик угла крышки** работает на:
- MacBook Pro 14"/16" (2021–2024, M1 Pro/Max — M4 Max)
- MacBook Air M2 (2022), M4 (2025)
- MacBook Pro 16" (2019, Intel)

**Fallback по яркости** работает на любом MacBook с внешним монитором.

Требуется macOS 14+ и подключённый внешний монитор.

## Установка

```bash
git clone https://github.com/n1x9s/display-switcher.git
cd display-switcher
chmod +x install.sh
./install.sh
```

Установщик:
1. Установит `displayplacer` через Homebrew (если нет)
2. Скомпилирует Swift-хелперы (датчик крышки + чтение яркости)
3. Проверит, что сенсоры работают на твоём маке
4. Настроит фоновый сервис (LaunchAgent)

## Настройка

Отредактируй `~/.config/display-switcher/switch.py`:

```python
LID_ANGLE_THRESHOLD = 60  # градусы — ниже этого значения переключается на внешний
```

После изменения перезапусти сервис:
```bash
launchctl unload ~/Library/LaunchAgents/com.display-switcher.plist
launchctl load ~/Library/LaunchAgents/com.display-switcher.plist
```

## Raycast

Скрипты в папке `raycast/`:
- **Switch Display by Lid/Brightness** — ручное переключение
- **Start Display Monitor** — запуск фонового мониторинга
- **Stop Display Monitor** — остановка мониторинга

Добавь папку `raycast/` в **Raycast → Settings → Extensions → Script Commands → Add Directory**.

## Ручное использование

```bash
# Узнать угол крышки
~/.config/display-switcher/lid-angle

# Узнать яркость
~/.config/display-switcher/brightness-helper

# Запустить один раз (проверить и переключить если нужно)
python3 ~/.config/display-switcher/switch.py

# Запуск/остановка фонового мониторинга
launchctl load ~/Library/LaunchAgents/com.display-switcher.plist
launchctl unload ~/Library/LaunchAgents/com.display-switcher.plist
```

## Удаление

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## Как это работает

1. **lid-angle** — Swift CLI, читает HID-датчик угла крышки (Apple VendorID 0x05AC, ProductID 0x8104) через IOKit
2. **brightness-helper** — Swift CLI, читает яркость встроенного экрана через приватный фреймворк DisplayServices
3. **switch.py** — Python-скрипт, каждые 2 секунды проверяет угол крышки (или яркость), сравнивает с порогом и вызывает `displayplacer` для переключения основного дисплея
4. После переключения перезапускается Dock (`killall Dock`), чтобы он сразу переехал на новый основной экран

## Credits

Чтение датчика угла крышки основано на [LidAngleSensor](https://github.com/samhenrigold/LidAngleSensor) by Sam Henri Gold.
