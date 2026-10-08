LaTeX → 한글 수식 도구 / Windows · macOS
버전 1.0 / 2026-10-08

가장 먼저 START_HERE.html을 열어 주세요.

[빠른 시작]
Windows: Python 3.10 이상 설치 → setup_windows.cmd 1회 실행 → run_windows.cmd
Mac: python.org의 Python 3.10 이상 설치 → run_mac.command
실행 스크립트와 Python 소스로 제공됩니다. 설치형 EXE/DMG는 포함하지 않습니다.

[공통]
수식을 입력 → HWPX 저장 → 한글에서 수식 문서 열기.
생성 파일에는 수정 가능한 한글 수식 개체가 들어 있습니다.
그 문서에서 수식을 복사해서 원하는 문서 본문에 붙여넣을 수 있습니다.
수식 한 개 / 문장 + 여러 수식 모드를 지원합니다.

[Windows 자동 입력]
도구를 실행해 둡니다. LaTeX를 복사한 뒤 한글 본문을 클릭하고 Ctrl+Alt+M.
또는 도구의 '한글에 자동 입력'을 누르고 5초 안에 한글 본문을 클릭합니다.
현재 한글 창의 자동화 연결을 확인할 수 없는 경우 입력하지 않습니다.
자동 입력은 한글 데스크톱 편집판과 pywin32가 필요합니다. 뷰어/웹한글은 대상이 아닙니다.
문서 선택 영역이 있다면 한글의 일반 입력 동작대로 대체될 수 있으니 커서만 놓아 주세요.
일반 Ctrl+V의 동작은 변경하지 않습니다. 앱을 닫으면 전역 단축키가 해제됩니다.

[Mac 자동 입력: 실험 기능]
'한글에 자동 입력'을 누르고 5초 안에 한글 본문을 클릭합니다.
이 기능은 수식 편집기를 내부적으로 열고 입력을 마칩니다.
macOS 손쉬운 사용/자동화 권한이 필요합니다. 요청에 표시된 실행 앱에 권한을 부여하세요.
한글 버전에 따라 수식 입력 칸을 읽을 수 없는 경우 자동 입력을 중단합니다.
이때 수식 창이 남아 있으면 취소하고 HWPX 저장을 사용하세요.
맥 자동 입력은 수식 한 개만 지원하고 글자 크기는 한글의 기본값을 따릅니다.
문장 + 여러 수식 및 크기 지정은 HWPX 저장으로 이용하세요.

Mac 단축키를 원하면 install_mac_shortcuts.command를 실행합니다.
시스템 설정 > 키보드 > 키보드 단축키 > 서비스에서:
  LaTeX_Hangul_Insert: Control+Option+Command+M (추천, 실험 자동 입력)
  LaTeX_Hangul_HWPX: Control+Option+Command+H (추천, HWPX 생성 후 열기)
다른 앱과 겹치면 다른 키를 정하세요. 로그아웃/로그인 후 나타나는 경우도 있습니다.
설치 뒤 이 폴더를 옮겼다면 설치 스크립트를 다시 실행하세요.
서비스 삭제: ~/Library/Services/ 안의 위 두 .workflow 폴더를 삭제합니다.
HWPX 서비스 출력 위치: ~/Documents/LaTeX-Hangul/

[수식 작성]
한 개: \frac{a+b}{2}
여러 개: 분수는 $\frac{a+b}{2}$입니다. 근호는 $\sqrt{2}$입니다.
다음 표기를 인식합니다: $...$, $$...$$, \(...\), \[...\]
문장 + 여러 수식 모드는 텍스트와 수식만 처리합니다. Markdown 표/그림/서식을 변환하지 않습니다.
여러 줄 행렬은 \begin{pmatrix} ... \end{pmatrix} 같은 지원 환경을 쓰세요.

[지원 범위]
분수, 제곱근/거듭제곱근, 위아래 첨자, 합, 곱, 극한, 적분,
삼각함수, 로그, 대표 그리스 문자, 집합/부등호, 조합, 벡터/막대,
matrix/pmatrix/bmatrix/vmatrix/cases 환경.
LaTeX 전체 문서, 사용자 매크로, TikZ, align/array, 일부 특수 명령은 지원하지 않습니다.
지원하지 않는 명령은 오류를 표시합니다. 지원하지 않는 수식을 임의로 바꾸어 넣지 않습니다.
한 수식 10,000자, 한 작업 200,000자 및 수식 200개까지.
긴 수식은 A4 본문 폭 검사에서 거절될 수 있습니다. 작게 하거나 나누어 주세요.

[검증 범위]
13개 자동 테스트를 통과했습니다. 알려진 수식의 변환, 잘못된 입력 거절,
문장/수식 순서 보존, XML 특수문자, HWPX ZIP/manifest/수식 개체 구조,
저장 실패 시 기존 파일 보존을 검사했습니다.
실제 Windows/macOS 한글에서 열기·수식 렌더링·자동 입력·단축키는 검증하지 못했습니다.
첫 사용은 빈 문서에서 sample_equations.hwpx와 분수 1/2로 확인해 주세요.
생성 문서의 수식 크기는 측정 모델을 사용하므로 한글 버전/글꼴에 따라 간격 차이가 날 수 있습니다.

[문제 해결]
Mac .command 실행 권한 오류: 터미널에서 이 폴더로 이동해 다음 실행:
  chmod +x run_mac.command install_mac_shortcuts.command
또는 같은 폴더에서 python3 app.py 실행.
Mac tkinter 없음: python.org 설치판을 사용하거나 CLI로 HWPX 생성.
Windows 자동화 연결 실패: 한글과 도구를 같은 사용자 권한으로 실행하고 현재 한글 본문을 클릭.
한글 뷰어는 편집/자동 입력을 지원하지 않습니다. 편집 가능한 한글이 필요합니다.

[개발자/명령줄]
python app.py --input examples.txt --document --output result.hwpx
python app.py --insert-clipboard
python app.py --clipboard-hwpx
python -m unittest discover -s tests -v
입력 내용은 실행하지 않으며 외부 서버로 전송하지 않습니다.
Windows 최초 의존성 설치 시에만 PyPI 다운로드에 인터넷이 필요합니다.

외부 소스/라이선스: THIRD_PARTY_NOTICES.txt, vendor/LICENSE-python-hwpx.txt
