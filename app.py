"""LaTeX → 한글 수식: cross-platform desktop UI and command line."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import queue
import subprocess
import sys
import traceback

from core import EXAMPLES, parse_document, write_hwpx
from native import WindowsHotkey, insert_mac, insert_windows, open_file


def clipboard_text() -> str:
    if sys.platform == "darwin":
        return subprocess.run(["/usr/bin/pbpaste"], capture_output=True, text=True, check=True).stdout
    import tkinter as tk
    temp = tk.Tk()
    temp.withdraw()
    try:
        return temp.clipboard_get()
    finally:
        temp.destroy()


def native_insert(parts, size_pt):
    if sys.platform == "win32":
        insert_windows(parts, size_pt)
    elif sys.platform == "darwin":
        insert_mac(parts, size_pt)
    else:
        raise RuntimeError("자동 입력은 Windows와 macOS에서 지원합니다. HWPX 저장은 모든 운영체제에서 가능합니다.")


def show_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("LaTeX → 한글 수식")
    root.geometry("920x790")
    root.minsize(740, 650)
    root.configure(bg="#F5F7FB")
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    family = "Apple SD Gothic Neo" if sys.platform == "darwin" else "Malgun Gothic"
    style.configure("TFrame", background="#F5F7FB")
    style.configure("TLabel", background="#F5F7FB", font=(family, 11))
    style.configure("TButton", font=(family, 11), padding=(12, 9))
    style.configure("Accent.TButton", background="#2563EB", foreground="white")
    style.map("Accent.TButton", background=[("active", "#1D4ED8")])
    body = ttk.Frame(root, padding=24)
    body.pack(fill="both", expand=True)
    ttk.Label(body, text="LaTeX → 한글 수식", font=(family, 23, "bold"), foreground="#16305B").pack(anchor="w")
    ttk.Label(body, text="수식을 붙여넣고, 한글에서 수정 가능한 수식으로 바꾸세요.", foreground="#52647E").pack(anchor="w", pady=(5, 16))

    settings = ttk.Frame(body)
    settings.pack(fill="x", pady=(0, 10))
    mode_label = tk.StringVar(value="수식 한 개")
    mode_box = ttk.Combobox(settings, state="readonly", textvariable=mode_label,
                            values=["수식 한 개", "문장 + 여러 수식"], width=19)
    mode_box.pack(side="left")
    ttk.Label(settings, text="  수식 크기").pack(side="left")
    size = tk.IntVar(value=12)
    ttk.Spinbox(settings, from_=8, to=32, width=4, textvariable=size).pack(side="left", padx=5)
    ttk.Label(settings, text="pt").pack(side="left")
    examples = ttk.Combobox(settings, state="readonly", values=list(EXAMPLES), width=17)
    examples.set("예제 선택")
    examples.pack(side="right")
    ttk.Label(body, text="1  LaTeX 입력", font=(family, 12, "bold")).pack(anchor="w", pady=(4, 6))
    source = ScrolledText(body, height=9, wrap="word", font=("Menlo" if sys.platform == "darwin" else "Consolas", 12),
                          padx=12, pady=12, relief="solid", borderwidth=1, undo=True)
    source.pack(fill="both", expand=True)
    source.insert("1.0", EXAMPLES["근의 공식"])
    ttk.Label(body, text="문장 + 여러 수식: 수식 부분을 $...$, $$...$$, \\( ... \\), \\[ ... \\]로 감싸 주세요.",
              foreground="#5B6B80", wraplength=840).pack(anchor="w", pady=(7, 10))

    bar = ttk.Frame(body)
    bar.pack(fill="x")
    status = tk.StringVar(value="준비 완료 · 입력 내용은 외부 서버로 전송하지 않습니다.")
    busy = {"value": False}
    events = queue.Queue()
    hotkey = None
    pending = {"id": None}

    def get_parts():
        if not 8 <= size.get() <= 32:
            raise ValueError("수식 크기는 8~32pt로 설정해 주세요.")
        return parse_document(source.get("1.0", "end-1c"), "formula" if mode_label.get() == "수식 한 개" else "document")

    def handle_error(exc):
        status.set("완료하지 못했습니다. 오류 안내를 확인해 주세요.")
        messagebox.showerror("확인이 필요합니다", str(exc), parent=root)

    def convert_now():
        try:
            parts = get_parts()
            result.configure(state="normal")
            result.delete("1.0", "end")
            result.insert("1.0", "\n\n".join(p.script for p in parts if p.kind == "equation"))
            result.configure(state="disabled")
            n = sum(p.kind == "equation" for p in parts)
            status.set(f"수식 {n}개 변환 완료 · HWPX로 저장하거나 한글에 자동 입력하세요.")
            return parts
        except Exception as exc:
            result.configure(state="normal")
            result.delete("1.0", "end")
            result.configure(state="disabled")
            handle_error(exc)
            return None

    def paste():
        try:
            value = root.clipboard_get()
            source.delete("1.0", "end")
            source.insert("1.0", value)
            convert_now()
        except Exception as exc:
            handle_error(exc)

    def choose_example(event=None):
        source.delete("1.0", "end")
        source.insert("1.0", EXAMPLES[examples.get()])
        mode_label.set("수식 한 개")
        convert_now()

    def copy_script():
        parts = convert_now()
        if parts is not None:
            root.clipboard_clear()
            root.clipboard_append("\n\n".join(p.script for p in parts if p.kind == "equation"))
            root.update_idletasks()
            status.set("한글 수식 코드 복사 완료 · 수식 편집기의 스크립트 칸에 붙여넣을 수 있습니다.")

    def export():
        parts = convert_now()
        if parts is None:
            return
        path = filedialog.asksaveasfilename(parent=root, title="편집 가능한 한글 수식 문서 저장",
                    defaultextension=".hwpx", filetypes=[("한글 표준 문서", "*.hwpx")], initialfile="수식변환.hwpx")
        if not path:
            return
        try:
            write_hwpx(parts, Path(path), size.get())
            status.set("HWPX 저장 완료 · 한글에서 열어 수식을 복사해 원하는 문서에 붙여넣으세요.")
            if open_after.get():
                open_file(Path(path))
        except Exception as exc:
            handle_error(exc)

    def do_insert(parts):
        try:
            native_insert(parts, size.get())
            if sys.platform == "darwin":
                status.set("수식 입력 요청 완료 · 맥 자동 입력의 글자 크기는 한글 수식 편집기의 기본값을 따릅니다.")
            else:
                status.set("한글에 입력했습니다. 문서에서 수식 모양을 확인해 주세요.")
        except Exception as exc:
            handle_error(exc)
        finally:
            busy["value"] = False
            insert_button.configure(state="normal")
            cancel_button.configure(state="disabled")
            pending["id"] = None

    def cancel_insert():
        if pending["id"]:
            root.after_cancel(pending["id"])
            pending["id"] = None
            busy["value"] = False
            insert_button.configure(state="normal")
            cancel_button.configure(state="disabled")
            status.set("자동 입력 예약을 취소했습니다.")

    def countdown(parts, remaining):
        if remaining:
            status.set(f"{remaining}초 뒤 입력합니다. 한글 문서에서 수식을 넣을 본문 위치를 클릭해 주세요.")
            pending["id"] = root.after(1000, countdown, parts, remaining - 1)
        else:
            do_insert(parts)

    def prepare_insert():
        if busy["value"]:
            return
        parts = convert_now()
        if parts is None:
            return
        if sys.platform == "darwin" and (len(parts) != 1 or parts[0].kind != "equation"):
            handle_error(ValueError("맥 자동 입력은 수식 한 개를 지원합니다. 문장 + 여러 수식은 HWPX로 저장해 주세요."))
            return
        busy["value"] = True
        insert_button.configure(state="disabled")
        cancel_button.configure(state="normal")
        countdown(parts, 5)

    ttk.Button(bar, text="클립보드 붙여넣기", command=paste).pack(side="left", padx=(0, 6))
    ttk.Button(bar, text="변환 확인", command=convert_now).pack(side="left", padx=6)
    ttk.Button(bar, text="HWPX 저장", style="Accent.TButton", command=export).pack(side="right")
    ttk.Label(body, text="2  한글 수식 코드", font=(family, 12, "bold")).pack(anchor="w", pady=(16, 6))
    result = ScrolledText(body, height=5, wrap="word", font=("Menlo" if sys.platform == "darwin" else "Consolas", 11),
                         padx=12, pady=12, background="#EEF3FB", relief="flat", state="disabled")
    result.pack(fill="both", expand=True)
    controls = ttk.Frame(body)
    controls.pack(fill="x", pady=(10, 8))
    ttk.Button(controls, text="수식 코드 복사", command=copy_script).pack(side="left")
    insert_button = ttk.Button(controls, text="한글에 자동 입력" + (" · 실험 기능" if sys.platform == "darwin" else ""), command=prepare_insert)
    insert_button.pack(side="left", padx=8)
    cancel_button = ttk.Button(controls, text="취소", command=cancel_insert, state="disabled")
    cancel_button.pack(side="left")
    open_after = tk.BooleanVar(value=True)
    ttk.Checkbutton(controls, text="저장 후 열기", variable=open_after).pack(side="right")
    info = "Windows: LaTeX 복사 → 한글 본문 클릭 → Ctrl+Alt+M. 도구가 실행 중이어야 합니다."
    if sys.platform == "darwin":
        info = "Mac: 자동 입력은 손쉬운 사용 권한이 필요하며 버전에 따라 작동하지 않을 수 있습니다. HWPX 저장은 별도 자동화 권한 없이 사용합니다."
    ttk.Label(body, text=info, wraplength=840, foreground="#52647E").pack(anchor="w", pady=(6, 8))
    ttk.Label(body, textvariable=status, wraplength=840, foreground="#1D4ED8").pack(anchor="w", pady=(3, 6))
    ttk.Label(body, text="이 패키지의 자동 입력은 실제 Windows/Mac 한글에서 아직 검증되지 않았습니다. 처음에는 빈 문서에서 확인해 주세요.",
              wraplength=840, font=(family, 9), foreground="#6B7280").pack(anchor="w")
    examples.bind("<<ComboboxSelected>>", choose_example)

    def poll():
        try:
            while True:
                kind, value = events.get_nowait()
                if kind == "hotkey" and not busy["value"]:
                    try:
                        parts = parse_document(root.clipboard_get(), "formula" if mode_label.get() == "수식 한 개" else "document")
                        busy["value"] = True
                        do_insert(parts)
                    except Exception as exc:
                        busy["value"] = False
                        handle_error(exc)
                elif kind == "error":
                    status.set(value)
                elif kind == "status":
                    status.set(value)
        except queue.Empty:
            pass
        root.after(120, poll)

    def close():
        cancel_insert()
        if hotkey:
            hotkey.close()
        root.destroy()

    if sys.platform == "win32":
        hotkey = WindowsHotkey(events)
    root.protocol("WM_DELETE_WINDOW", close)
    poll()
    convert_now()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="오프라인 LaTeX → 한글 수식 변환")
    parser.add_argument("--input", type=Path, help="UTF-8 LaTeX 텍스트 파일")
    parser.add_argument("--output", type=Path, help="저장할 .hwpx 파일")
    parser.add_argument("--document", action="store_true", help="문장 + 여러 수식 모드")
    parser.add_argument("--size", type=int, default=12)
    parser.add_argument("--insert-clipboard", action="store_true", help="현재 클립보드 수식을 현재 한글 창에 삽입")
    parser.add_argument("--clipboard-hwpx", action="store_true", help="현재 클립보드 수식을 HWPX로 저장 후 열기")
    args = parser.parse_args()
    if not args.input and not args.insert_clipboard and not args.clipboard_hwpx:
        show_gui()
        return 0
    try:
        if not 8 <= args.size <= 32:
            raise ValueError("수식 크기는 8~32pt여야 합니다.")
        source = args.input.read_text(encoding="utf-8-sig") if args.input else clipboard_text()
        parts = parse_document(source, "document" if args.document else "formula")
        if args.insert_clipboard:
            native_insert(parts, args.size)
        elif args.clipboard_hwpx:
            target = args.output or (Path.home() / "Documents" / "LaTeX-Hangul" / (datetime.now().strftime("equation_%Y%m%d_%H%M%S_%f") + ".hwpx"))
            write_hwpx(parts, target, args.size)
            open_file(target)
        elif args.output:
            write_hwpx(parts, args.output, args.size)
            print(f"저장 완료: {args.output}")
        else:
            print("\n\n".join(p.script for p in parts if p.kind == "equation"))
        return 0
    except Exception as exc:
        print(f"오류: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
