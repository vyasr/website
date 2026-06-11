#!/usr/bin/env bash
set -euo pipefail

python3 scripts/generate_bibliography.py --data-root external/cv-data --output-root content

if [ ! -d external/awesome-cv/.git ]; then
  echo "Cloning Awesome-CV for local CV build..."
  git clone --recurse-submodules https://github.com/vyasr/Awesome-CV.git external/awesome-cv
fi

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
