#!/usr/bin/env bash
# =====================================================================
#  Сборка диаграмм PlantUML: lab/diagrams/src/*.puml -> lab/diagrams/generated/*.png
#
#  Рендерер ищется в таком порядке:
#    1. переменная окружения PLANTUML_CMD (полная команда);
#    2. команда `plantuml` в PATH;
#    3. переменная окружения PLANTUML_JAR (путь к plantuml.jar);
#    4. файл lab/diagrams/plantuml.jar;
#    5. файл ~/.local/tools/plantuml.jar;
#    6. Docker-образ plantuml/plantuml.
#
#  C4-диаграммы используют локально сохранённый stdlib
#  (lab/diagrams/stdlib/C4*.puml) через -DRELATIVE_INCLUDE=1, поэтому
#  сборка не требует доступа в интернет.
# =====================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
OUT_DIR="$SCRIPT_DIR/generated"
LOCAL_JAR="$SCRIPT_DIR/plantuml.jar"
FALLBACK_JAR="$HOME/.local/tools/plantuml.jar"

mkdir -p "$OUT_DIR"

# Диаграммы вида C4 используют graphviz (dot) для раскладки блоков --
# jar-рендереры без установленного dot дают "рабочий" (нулевой код
# возврата), но битый PNG, поэтому неявные варианты 4-5 пропускаются,
# если dot не найден в PATH (явные PLANTUML_CMD/PLANTUML_JAR считаются
# осознанным выбором пользователя и не проверяются).
HAVE_DOT=0
command -v dot >/dev/null 2>&1 && HAVE_DOT=1

if [ -n "${PLANTUML_CMD:-}" ]; then
  RENDER=("$PLANTUML_CMD" -DRELATIVE_INCLUDE=1 -tpng -o "$OUT_DIR" "$SRC_DIR"/*.puml)
elif command -v plantuml >/dev/null 2>&1; then
  RENDER=(plantuml -DRELATIVE_INCLUDE=1 -tpng -o "$OUT_DIR" "$SRC_DIR"/*.puml)
elif [ -n "${PLANTUML_JAR:-}" ] && [ -f "${PLANTUML_JAR:-}" ]; then
  RENDER=(java -DRELATIVE_INCLUDE=1 -jar "$PLANTUML_JAR" -tpng -o "$OUT_DIR" "$SRC_DIR"/*.puml)
elif [ -f "$LOCAL_JAR" ] && [ "$HAVE_DOT" -eq 1 ]; then
  RENDER=(java -DRELATIVE_INCLUDE=1 -jar "$LOCAL_JAR" -tpng -o "$OUT_DIR" "$SRC_DIR"/*.puml)
elif [ -f "$FALLBACK_JAR" ] && [ "$HAVE_DOT" -eq 1 ]; then
  RENDER=(java -DRELATIVE_INCLUDE=1 -jar "$FALLBACK_JAR" -tpng -o "$OUT_DIR" "$SRC_DIR"/*.puml)
elif command -v docker >/dev/null 2>&1; then
  echo "Рендерю через Docker-образ plantuml/plantuml..."
  docker run --rm -v "$SCRIPT_DIR:/diagrams" plantuml/plantuml \
    -DRELATIVE_INCLUDE=1 -tpng -o /diagrams/generated /diagrams/src
  exit 0
else
  echo "Не найден рендерер PlantUML." >&2
  echo "Установите одно из:" >&2
  echo "  - переменную PLANTUML_CMD или PLANTUML_JAR;" >&2
  echo "  - команду 'plantuml' в PATH;" >&2
  echo "  - $LOCAL_JAR или $FALLBACK_JAR;" >&2
  echo "  - Docker." >&2
  exit 1
fi

"${RENDER[@]}"
echo "Диаграммы собраны в $OUT_DIR"
