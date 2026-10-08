"""OS bridges. No server, clipboard monitoring, or document auto-save."""
from __future__ import annotations

import json
from pathlib import Path
import queue
import subprocess
import sys
import threading

ROOT = Path(__file__).resolve().parent


def open_file(path: Path) -> None:
    if sys.platform == "win32":
        import os
        os.startfile(str(path))
    elif sys.platform == "darwin":
        subprocess.run(["/usr/bin/open", str(path)], check=True)
    else:
        subprocess.Popen(["xdg-open", str(path)])


def _windows_target():
    try:
        import pythoncom
        import win32api
        import win32com.client
        import win32gui
        import win32process
    except ImportError as exc:
        raise RuntimeError("윈도우 자동 입력에는 pywin32가 필요합니다. setup_windows.cmd를 한 번 실행해 주세요.") from exc
    foreground = win32gui.GetForegroundWindow()
    pid = win32process.GetWindowThreadProcessId(foreground)[1]
    try:
        handle = win32api.OpenProcess(0x1000, False, pid)
        try:
            import ctypes
            from ctypes import wintypes
            kernel = ctypes.WinDLL("kernel32", use_last_error=True)
            query = kernel.QueryFullProcessImageNameW
            query.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
            query.restype = wintypes.BOOL
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            if not query(int(handle), 0, buffer, ctypes.byref(length)):
                raise OSError("프로세스 이름을 확인할 수 없습니다.")
            executable = Path(buffer.value).name.lower()
        finally:
            handle.Close()
    except Exception as exc:
        raise RuntimeError("현재 창이 한글인지 확인하지 못했습니다. 한글 본문을 클릭하고 다시 시도해 주세요.") from exc
    if executable != "hwp.exe":
        raise RuntimeError("현재 선택된 창이 한글이 아닙니다. 한글 문서의 본문을 클릭해 주세요.")
    pythoncom.CoInitialize()
    candidates = []
    try:
        candidates.append(win32com.client.GetActiveObject("HWPFrame.HwpObject"))
    except Exception:
        pass
    rot = pythoncom.GetRunningObjectTable()
    for moniker in rot.EnumRunning():
        try:
            name = moniker.GetDisplayName(pythoncom.CreateBindCtx(0), None)
            if "hwpobject" in name.lower():
                dispatch = rot.GetObject(moniker).QueryInterface(pythoncom.IID_IDispatch)
                candidates.append(win32com.client.Dispatch(dispatch))
        except Exception:
            continue
    for candidate in candidates:
        try:
            hwnd = int(candidate.XHwpWindows.Active_XHwpWindow.WindowHandle)
            if hwnd == foreground:
                return candidate
        except Exception:
            continue
    raise RuntimeError("현재 한글 창의 자동화 연결을 찾지 못했습니다. 한글과 도구를 같은 사용자 권한으로 실행해 주세요. 계속 실패하면 HWPX 저장을 이용해 주세요.")


def insert_windows(parts, size_pt: int = 12) -> None:
    hwp = _windows_target()
    inserted = 0
    try:
        for part in parts:
            if part.kind == "text":
                params = hwp.HParameterSet.HInsertText
                hwp.HAction.GetDefault("InsertText", params.HSet)
                params.Text = part.source
                success = hwp.HAction.Execute("InsertText", params.HSet)
            else:
                params = hwp.HParameterSet.HEqEdit
                hwp.HAction.GetDefault("EquationCreate", params.HSet)
                params.String = part.script
                params.BaseUnit = size_pt * 100
                params.EqFontName = "HYhwpEQ"
                success = hwp.HAction.Execute("EquationCreate", params.HSet)
            if not success:
                raise RuntimeError("한글이 입력 요청을 처리하지 못했습니다.")
            inserted += 1
    except Exception as exc:
        raise RuntimeError(f"자동 입력이 중단되었습니다. 처리된 항목: {inserted}개. 문서를 확인하고 필요하면 한글에서 실행 취소해 주세요.\n{exc}") from exc


def insert_mac(parts, size_pt: int = 12) -> None:
    # Single equation only: every click must be scoped to the equation dialog.
    if len(parts) != 1 or parts[0].kind != "equation":
        raise RuntimeError("맥 자동 입력은 수식 한 개를 지원합니다. 문장 + 여러 수식은 HWPX 저장을 이용해 주세요.")
    result = subprocess.run(
        ["/usr/bin/osascript", str(ROOT / "mac_insert.applescript"), parts[0].script],
        capture_output=True, text=True, timeout=25,
    )
    if result.returncode:
        raise RuntimeError("맥 자동 입력을 완료하지 못했습니다.\n" + result.stderr.strip() +
                           "\n한글 수식 창이 열려 있다면 취소 후 HWPX 저장을 이용해 주세요.")


class WindowsHotkey:
    """Ctrl+Alt+M is active only while the tool runs; Ctrl+V is untouched."""
    def __init__(self, events: queue.Queue):
        self.events = events
        self.thread_id = None
        self.ready = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        import ctypes
        from ctypes import wintypes
        user = ctypes.WinDLL("user32", use_last_error=True)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.thread_id = kernel.GetCurrentThreadId()
        message = wintypes.MSG()
        user.PeekMessageW(ctypes.byref(message), None, 0, 0, 0)
        # MOD_NOREPEAT, MOD_CONTROL, MOD_ALT.
        if not user.RegisterHotKey(None, 1, 0x4000 | 0x2 | 0x1, ord("M")):
            self.events.put(("error", "Ctrl+Alt+M 단축키를 등록하지 못했습니다. 다른 프로그램이 사용 중일 수 있습니다. 자동 입력 버튼은 사용할 수 있습니다."))
            self.ready.set()
            return
        self.ready.set()
        self.events.put(("status", "단축키 준비 완료 · 한글에서 Ctrl+Alt+M"))
        try:
            while user.GetMessageW(ctypes.byref(message), None, 0, 0) > 0:
                if message.message == 0x312:
                    self.events.put(("hotkey", None))
        finally:
            user.UnregisterHotKey(None, 1)

    def close(self):
        if self.thread_id:
            import ctypes
            ctypes.windll.user32.PostThreadMessageW(self.thread_id, 0x12, 0, 0)
