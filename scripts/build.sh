#!/usr/bin/env bash
set -euo pipefail

python3 scripts/generate_bibliography.py --data-root external/cv-data --output-root content

if [ ! -d external/awesome-cv/.git ]; then
  echo "Cloning Awesome-CV for local CV build..."
  git clone --recurse-submodules https://github.com/vyasr/Awesome-CV.git external/awesome-cv
fi

if command -v xelatex >/dev/null 2>&1 && command -v latexmk >/dev/null 2>&1; then
  make -C external/awesome-cv/mycv build

  if [ -f external/awesome-cv/mycv/cv.pdf ]; then
    mkdir -p static/files
    cp external/awesome-cv/mycv/cv.pdf static/files/cv.pdf
  fi
fi

hugo
