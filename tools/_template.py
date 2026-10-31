"""새 도구 템플릿. 복사해서 tools/내_도구.py 로 저장하고 채운다.
(`_` 로 시작하는 파일은 자동 탐색에서 제외된다.)

규칙: tools/ 는 core 만 import 한다. ui / textual / runner import 금지.
"""
from core import Field, Tool


def run(config, ctx):
    """config = {필드 key: 값, ..., "_pressed": 눌린 버튼 key}.
    ctx.log / ctx.progress / ctx.sleep / ctx.check_cancel / ctx.confirm 만 사용한다.
    끝나면 그냥 return (프로그램은 종료되지 않고 같은 화면에 남는다)."""
    ctx.log(f"start: {config}")
    for i in range(1, 6):
        ctx.sleep(0.5)               # 취소되면 CancelledError (그대로 통과시키면 됨)
        ctx.progress(i * 20, f"step {i}/5")
    ctx.log("done")


tool = Tool(
    id="template",
    name="Template",                  # 홈 목록의 이름 줄 / 도구 창 제목
    description="Copy this file",     # 홈 목록의 설명 줄 (비우면 표시 안 함)
    fields=[
        Field("input_file", "file", "1. Input File:", placeholder="press Enter to browse"),
        # Field("input_files", "file", "1. Input Files:", multi=True),   # 여러 개 선택: 값 = 경로 리스트
        [   # 한 줄에 2개
            Field("mode", "cycle", "2. Mode:", options=["Fast", "Balanced", "Quality"]),
            Field("name", "input", "3. Name:", placeholder="type something..."),
        ],
    ],
    run=run,
    run_label="RUN",
    # allowed_ext=(".mp4", ".mkv"),
    # output_dir_name="Output",   # 반드시 "Output" (모든 도구 공유). 도구별 폴더명 금지
    # texts={"STATUS_READY_TEXT": "Idle"},
)
