#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
if [[ -x /Library/Frameworks/Python.framework/Versions/Current/bin/python3 ]]; then
  runner=/Library/Frameworks/Python.framework/Versions/Current/bin/python3
else
  runner=$(command -v python3)
fi
if [[ -z "$runner" ]]; then
  print '먼저 Python을 설치해 주세요: https://www.python.org/downloads/macos/'
else
  "$runner" install_mac_shortcuts.py
fi
read '?Return 키를 누르면 닫습니다.'
