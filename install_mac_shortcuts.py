"""Install two user-invoked Automator Quick Actions; no background daemon."""
from pathlib import Path
import plistlib
import shlex
import sys
import uuid


def workflow(command):
    return {
        "AMApplicationBuild": "523", "AMApplicationVersion": "2.10", "AMDocumentVersion": "2",
        "actions": [{"action": {
            "AMAccepts": {"Container": "List", "Optional": True, "Types": ["com.apple.cocoa.string"]},
            "AMActionVersion": "2.0.3", "AMApplication": ["Automator"],
            "AMParameterProperties": {k: {} for k in ["COMMAND_STRING", "CheckedForUserDefaultShell", "inputMethod", "shell"]},
            "AMProvides": {"Container": "List", "Types": ["com.apple.cocoa.string"]},
            "ActionBundlePath": "/System/Library/Automator/Run Shell Script.action",
            "ActionName": "Run Shell Script",
            "ActionParameters": {"COMMAND_STRING": command, "CheckedForUserDefaultShell": True, "inputMethod": 0, "shell": "/bin/zsh"},
            "BundleIdentifier": "com.apple.RunShellScript", "CFBundleVersion": "2.0.3",
            "CanShowSelectedItemsWhenRun": False, "CanShowWhenRun": True,
            "Category": ["AMCategoryUtilities"], "Class Name": "RunShellScriptAction",
            "InputUUID": str(uuid.uuid4()), "OutputUUID": str(uuid.uuid4()),
            "UUID": str(uuid.uuid4()), "isViewVisible": True,
        }, "isViewVisible": True}],
        "connectors": [],
        "workflowMetaData": {
            "workflowTypeIdentifier": "com.apple.Automator.servicesMenu",
            "serviceInputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceOutputTypeIdentifier": "com.apple.Automator.nothing",
            "serviceProcessesInput": 0,
            "serviceApplicationBundleID": "", "serviceApplicationPath": "",
            "serviceMenuTitle": "LaTeX to Hangul", "useAutomaticInputType": False,
        },
    }


def main():
    if sys.platform != "darwin":
        raise SystemExit("이 설치 파일은 macOS에서 실행해 주세요.")
    root = Path(__file__).resolve().parent
    service_dir = Path.home() / "Library" / "Services"
    for name, flag in [("LaTeX_Hangul_Insert", "--insert-clipboard"), ("LaTeX_Hangul_HWPX", "--clipboard-hwpx")]:
        # User-facing fixed alert; captured text is passed as argv, never as code.
        command = f'''set -eu
cd -- {shlex.quote(str(root))}
if ! result=$({shlex.quote(sys.executable)} app.py {flag} 2>&1); then
  /usr/bin/osascript - "$result" <<'APPLESCRIPT'
on run argv
  display alert "LaTeX → 한글 수식" message (item 1 of argv) as warning
end run
APPLESCRIPT
fi
'''
        target = service_dir / (name + ".workflow") / "Contents"
        target.mkdir(parents=True, exist_ok=True)
        data = workflow(command)
        data["workflowMetaData"]["serviceMenuTitle"] = name
        (target / "document.wflow").write_bytes(plistlib.dumps(data))
        print(f"설치: {name}")
    print("시스템 설정 → 키보드 → 키보드 단축키 → 서비스에서 단축키를 지정하세요.")
    print("Insert는 실험 기능입니다. 작동하지 않으면 HWPX 서비스를 사용하세요.")


if __name__ == "__main__":
    main()
