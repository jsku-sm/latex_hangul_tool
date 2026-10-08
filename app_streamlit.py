"""Streamlit web interface for the LaTeX-to-Hangul equation converter."""
from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

from core import EXAMPLES, parse_document, write_hwpx


st.set_page_config(page_title="LaTeX → 한글 수식", layout="wide")
st.title("LaTeX → 한글 수식")
st.caption("LaTeX를 한글 수식 코드로 변환하고 편집 가능한 HWPX 문서로 저장합니다.")

if "source" not in st.session_state:
    st.session_state.source = EXAMPLES.get("근의 공식", next(iter(EXAMPLES.values()), ""))

left, middle, right = st.columns([2, 1, 2])
with left:
    mode = st.selectbox("변환 모드", ["수식 한 개", "문장 + 여러 수식"])
with middle:
    size = st.number_input("수식 크기 (pt)", min_value=8, max_value=32, value=12, step=1)
with right:
    example = st.selectbox("예제 선택", ["직접 입력", *EXAMPLES.keys()])

if example != "직접 입력":
    # Update the editor only when the selected example changes.
    if st.session_state.get("last_example") != example:
        st.session_state.source = EXAMPLES[example]
st.session_state.last_example = example

source = st.text_area("1. LaTeX 입력", key="source", height=220)
st.caption(r"문장 + 여러 수식 모드에서는 수식을 $...$, $$...$$, \(...\), \[...\]로 감싸세요.")

if st.button("변환 확인", type="primary"):
    try:
        parts = parse_document(source, "formula" if mode == "수식 한 개" else "document")
        scripts = "\n\n".join(part.script for part in parts if part.kind == "equation")
        count = sum(part.kind == "equation" for part in parts)
        with TemporaryDirectory() as directory:
            output = Path(directory) / "수식변환.hwpx"
            write_hwpx(parts, output, int(size))
            document = output.read_bytes()
        st.session_state.result = {"scripts": scripts, "count": count, "document": document}
    except Exception as exc:
        st.session_state.pop("result", None)
        st.error(f"변환 실패: {exc}")

if "result" in st.session_state:
    result = st.session_state.result
    st.success(f"수식 {result['count']}개 변환 완료")
    st.text_area("2. 한글 수식 코드 (선택하여 복사)", value=result["scripts"], height=160)
    st.download_button(
        "HWPX 파일 다운로드",
        data=result["document"],
        file_name="수식변환.hwpx",
        mime="application/octet-stream",
    )

st.info("웹에서는 PC의 한글 프로그램에 자동 입력할 수 없습니다. HWPX 파일을 내려받아 한글에서 열어주세요.")
