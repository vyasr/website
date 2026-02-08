#!/usr/bin/env bash
set -euo pipefail

python3 scripts/generate_bibliography.py --cv-root external/awesome-cv --output-root content

if command -v xelatex >/dev/null 2>&1; then
  make -C external/awesome-cv/mycv cv.pdf
  if [ -f external/awesome-cv/mycv/cv.pdf ]; then
    cp external/awesome-cv/mycv/cv.pdf static/files/cv.pdf
  fi
fi

hugo
