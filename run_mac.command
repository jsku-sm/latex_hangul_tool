#!/bin/zsh
cd -- "$(dirname -- "$0")" || exit 1
if [[ -x /Library/Frameworks/Python.framework/Versions/Current/bin/python3 ]]; then
  runner=/Library/Frameworks/Python.framework/Versions/Current/bin/python3
else
  runner=$(command -v python3)
fi
if [[ -z "$runner" ]] || ! "$runner" -c 'import sys, tkinter; assert sys.version_info >= (3, 10)' 2>/dev/null; then
  print 'Python 3.10 이상과 tkinter가 필요합니다. https://www.python.org/downloads/macos/ 의 설치판을 사용하세요.'
  read '?Return 키를 누르면 닫습니다.'
  exit 1
fi
"$runner" app.py
if [[ $? -ne 0 ]]; then
  read '?실행 오류가 발생했습니다. Return 키를 누르면 닫습니다.'
fi
