#!/usr/bin/env bash
set -euo pipefail

python3 scripts/generate_bibliography.py --cv-root external/awesome-cv --output-root content

if command -v xelatex >/dev/null 2>&1; then
  if command -v biber >/dev/null 2>&1; then
    (cd external/awesome-cv/mycv && xelatex -interaction=nonstopmode cv.tex >/dev/null)
    (cd external/awesome-cv/mycv && biber cv >/dev/null)
    (cd external/awesome-cv/mycv && xelatex -interaction=nonstopmode cv.tex >/dev/null)
    (cd external/awesome-cv/mycv && xelatex -interaction=nonstopmode cv.tex >/dev/null)
  else
    (cd external/awesome-cv/mycv && xelatex -interaction=nonstopmode cv.tex >/dev/null)
  fi

  if [ -f external/awesome-cv/mycv/cv.pdf ]; then
    cp external/awesome-cv/mycv/cv.pdf static/files/cv.pdf
  fi
fi

hugo
