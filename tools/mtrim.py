# -*- coding: utf-8 -*-
"""미디어 트리머 (ffmpeg 기반). 재인코딩 없이(-c copy) 구간만 잘라 Output/ 에 저장한다.

규칙: tools/ 는 core 만 import 한다. ui / textual / runner import 금지.
"""
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime

from core import Field, Tool

OUTPUT_DIR_NAME = "Output"   # 모든 도구가 공유하는 폴더 (AGENT.md 참고)
FFMPEG_PATH = "ffmpeg"
ALLOWED_EXT = (".mp4", ".mkv", ".avi", ".mov", ".flv", ".mp3", ".wav", ".m4a", ".flac", ".ts")
POLL_INTERVAL = 0.2          # ffmpeg 종료 확인 / 취소 확인 주기(초)
KILL_WAIT = 3.0              # 취소 시 ffmpeg 가 종료되길 기다리는 최대 시간(초)

_TIME_PLAIN_RE = re.compile(r"^\d+(\.\d+)?$")
_TIME_CLOCK_RE = re.compile(r"^(\d+:){1,2}\d+(\.\d+)?$")


# ==============================================================================
# 시간 파싱 / 변환
# ==============================================================================
def time_to_seconds(time_str: str) -> float:
    time_str = time_str.strip()
    if not time_str:
        return 0.0

    main_part, *ms_part = time_str.split(".")
    ms_val = float(f"0.{ms_part[0]}") if ms_part else 0.0

    tokens = main_part.split(":")
    if len(tokens) == 1:
        return float(tokens[0]) + ms_val
    elif len(tokens) == 2:
        return int(tokens[0]) * 60 + int(tokens[1]) + ms_val
    elif len(tokens) == 3:
        return int(tokens[0]) * 3600 + int(tokens[1]) * 60 + int(tokens[2]) + ms_val
    return 0.0


def seconds_to_ffmpeg_format(seconds: float) -> str:
    total_ms = int(round(seconds * 1000))   # 먼저 밀리초로 반올림 (4.9996초 -> '.1000' 같은 오류 방지)
    secs_total, ms = divmod(total_ms, 1000)
    hrs, rest = divmod(secs_total, 3600)
    mins, secs = divmod(rest, 60)

    if ms > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}.{ms:03d}"
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


def parse_and_normalize_time(time_str: str) -> tuple:
    time_str = time_str.strip()
    if not time_str:
        return "00:00:00", 0.0

    if _TIME_PLAIN_RE.match(time_str):
        secs = float(time_str)
        return seconds_to_ffmpeg_format(secs), secs

    if _TIME_CLOCK_RE.match(time_str):
        secs = time_to_seconds(time_str)
        return seconds_to_ffmpeg_format(secs), secs

    raise ValueError(f"Unrecognized time format: '{time_str}'")


# ==============================================================================
# Job 빌드
# ==============================================================================
def build_job(file_path: str, values: dict, log_fn) -> dict:
    start_raw = values.get("start") or ""
    end_raw = values.get("end") or ""

    if not file_path or not os.path.exists(file_path):
        raise FileNotFoundError("Input file does not exist.")

    start_normalized, start_secs = parse_and_normalize_time(start_raw)

    duration_formatted = None
    if end_raw.strip():
        end_normalized, end_secs = parse_and_normalize_time(end_raw)
        if end_secs <= start_secs:
            raise ValueError("End time must be after start time.")
        duration_formatted = seconds_to_ffmpeg_format(end_secs - start_secs)
        log_fn(f"[DEBUG][MATH] Duration: {duration_formatted}")
    else:
        end_normalized = None

    log_fn(f"[DEBUG][PARSE] Start: {start_normalized}")
    if end_normalized:
        log_fn(f"[DEBUG][PARSE] End: {end_normalized}")

    # 프로젝트 루트(tools/ 의 상위 폴더)의 Output/
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(project_root, OUTPUT_DIR_NAME)
    os.makedirs(output_dir, exist_ok=True)

    # 다른 도구/이전 결과와 파일명이 겹치지 않게 도구 이름 + 시각을 붙인다 (입력이 Output/ 안에 있어도 안전)
    stem, ext = os.path.splitext(os.path.basename(file_path))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(output_dir, f"{stem}_trim_{stamp}{ext}")

    cmd = [FFMPEG_PATH, "-y", "-ss", start_normalized, "-i", file_path]
    if duration_formatted:
        cmd.extend(["-t", duration_formatted])
    cmd.extend(["-c", "copy", output_path])

    log_fn(f"[DEBUG][COMMAND] {' '.join(cmd)}")
    return {"cmd": cmd, "output_path": output_path}


# ==============================================================================
# 실행
# ==============================================================================
def _stop_process(proc) -> None:
    """ffmpeg 를 종료한다 (정상 종료 요청 -> 안 되면 강제 종료)."""
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
        proc.wait(timeout=KILL_WAIT)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _remove_quietly(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def run(config, ctx):
    ctx.log("[INFO] MEDIA TRIMMER started")

    if shutil.which(FFMPEG_PATH) is None:
        raise RuntimeError(f"'{FFMPEG_PATH}' not found. Install ffmpeg and add it to PATH.")

    # 잘못된 입력은 예외로 던진다 -> 상태줄에 에러가 표시되고 로그에 남는다
    job = build_job(config.get("file") or "", config, ctx.log)
    ctx.check_cancel()

    # 원본은 완료 여부만 확인하고 진행률(%)을 계산하지 않았으므로 percent 는 None 으로 유지한다
    ctx.progress(None, "Running ffmpeg...")

    # stderr 는 파이프 대신 임시 파일로 받는다 (출력이 많아도 ffmpeg 가 막히지 않게)
    stderr_file = tempfile.NamedTemporaryFile(
        mode="w+", encoding="utf-8", errors="replace", delete=False
    )
    proc = None
    try:
        proc = subprocess.Popen(job["cmd"], stdout=subprocess.DEVNULL, stderr=stderr_file)
        ctx.log(f"[DEBUG][RUN] ffmpeg started (pid={proc.pid})")
        while proc.poll() is None:
            ctx.sleep(POLL_INTERVAL)   # 취소되면 CancelledError -> 아래 finally 에서 ffmpeg 정리
    except BaseException:
        if proc is not None:
            _stop_process(proc)
            _remove_quietly(job["output_path"])   # 취소/오류로 남은 불완전한 결과 파일 삭제
        raise
    finally:
        stderr_file.close()

    try:
        with open(stderr_file.name, "r", encoding="utf-8", errors="replace") as f:
            stderr = f.read()
    finally:
        _remove_quietly(stderr_file.name)

    if proc.returncode != 0:
        ctx.log("[ERROR] ffmpeg exited with a non-zero status.")
        for line in stderr.splitlines():
            ctx.log(line)
        _remove_quietly(job["output_path"])
        raise RuntimeError(f"ffmpeg failed (code {proc.returncode}) - press '/' for log")

    ctx.log("[DEBUG][SUCCESS] ffmpeg finished cleanly.")
    ctx.log(f"[DEBUG][OUTPUT] {job['output_path']}")
    if stderr:
        ctx.log("--- ffmpeg stderr ---")
        for line in stderr.splitlines():
            ctx.log(line)


tool = Tool(
    id="mtrim",
    name="Media Trimmer",
    description="Cut a time range",
    category="Editor",
    fields=[
        Field("file", "file", "1. Target File Path:"),
        [
            Field("start", "input", "2. Start Time:", placeholder="HH:MM:SS"),
            Field("end", "input", "3. End Time:", placeholder="Blank = EOF"),
        ],
    ],
    run=run,
    run_label="RUN TRIMMING PASS",
    allowed_ext=ALLOWED_EXT,
    output_dir_name="Output",
)
