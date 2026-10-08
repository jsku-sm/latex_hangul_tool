-- Mac Hangul: use Accessibility only within a verified equation dialog.
-- Hancom 2022 documented shortcuts: Control+N,M; Shift+Escape.
-- Actual accessibility tree varies by release; refuse ambiguous controls.
on run argv
    if (count argv) is not 1 then error "수식 인수가 없습니다."
    set equationText to item 1 of argv
    tell application "System Events"
        set targetProcess to first application process whose frontmost is true
        set processName to name of targetProcess
        set bundleName to bundle identifier of targetProcess
        ignoring case
            if bundleName does not contain "hancom" and bundleName does not contain "haansoft" then
                error "한글 문서 본문을 클릭한 뒤 다시 실행해 주세요."
            end if
            if processName does not contain "한글" and processName does not contain "hwp" and processName does not contain "Hanword" and processName does not contain "Hangul" then
                error "현재 창을 한글로 확인하지 못했습니다. HWPX 저장을 이용해 주세요."
            end if
        end ignoring
        tell targetProcess
            if (count of windows) is 0 then error "먼저 한글 문서를 열어 주세요."
            -- Key codes avoid dependence on the currently selected Korean IME.
            key code 45 using {control down}
            delay 0.15
            key code 46
            set eqDialog to missing value
            repeat 25 times
                repeat with w in windows
                    if name of w contains "수식" or name of w contains "Equation" then
                        set eqDialog to contents of w
                        exit repeat
                    end if
                    repeat with s in sheets of w
                        if name of s contains "수식" or name of s contains "Equation" then
                            set eqDialog to contents of s
                            exit repeat
                        end if
                    end repeat
                end repeat
                if eqDialog is not missing value then exit repeat
                delay 0.15
            end repeat
            if eqDialog is missing value then error "수식 편집기 창을 확인하지 못했습니다. 본문에는 입력하지 않았습니다."
            set textCandidates to {}
            set scriptBox to missing value
            repeat with el in entire contents of eqDialog
                try
                    set roleName to role of el
                    if roleName is "AXTextArea" or roleName is "AXTextField" then
                        set labelText to (description of el as text) & " " & (name of el as text)
                        if labelText contains "스크립트" or labelText contains "명령어" or labelText contains "script" then
                            set scriptBox to contents of el
                            exit repeat
                        end if
                        if roleName is "AXTextArea" then set end of textCandidates to contents of el
                    end if
                end try
            end repeat
            if scriptBox is missing value and (count of textCandidates) is 1 then set scriptBox to item 1 of textCandidates
            if scriptBox is missing value then error "수식의 스크립트 입력 칸을 구분하지 못했습니다. 이 한글 버전에서는 HWPX 저장을 이용해 주세요."
            if not (settable of attribute "AXValue" of scriptBox) then error "이 버전에서는 수식 입력 칸을 자동으로 편집할 수 없습니다. HWPX 저장을 이용해 주세요."
            set value of attribute "AXValue" of scriptBox to equationText
            delay 0.2
            if (value of attribute "AXValue" of scriptBox as text) is not equationText then error "입력 확인에 실패했습니다. 수식 편집기에서 내용을 확인해 주세요."
            key code 53 using {shift down}
        end tell
    end tell
    return "수식 입력 요청 완료"
end run
