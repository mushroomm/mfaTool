#!/usr/bin/env python3
"""One-click pipeline: audio/video -> transcript -> MFA alignment -> final pinyin TextGrid."""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

from mfa2pinyin import generate as generate_pinyin_textgrid

AUDIO_VIDEO_EXTENSIONS = {
    ".wav",
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".aac",
    ".wma",
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".webm",
}

PUNCTUATION_RE = re.compile(
    r"[\s\u3000\.,!?;:'\"`~@#$%^&*()_+\-=\[\]{}\\|/<>"
    r"，。！？；：、“”‘’（）《》〈〉【】『』「」—…·￥]+"
)


def repo_root() -> Path:
    return Path(__file__).resolve().parent


def clean_transcript(text: str) -> str:
    """Remove punctuation/spaces and split every remaining character with spaces."""
    compact = PUNCTUATION_RE.sub("", text)
    return " ".join(compact)


def media_files(audio_dir: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(audio_dir.iterdir()):
        if not path.is_file() or path.suffix.lower() not in AUDIO_VIDEO_EXTENSIONS:
            continue
        if path.suffix.lower() != ".wav" and path.with_suffix(".wav").exists():
            continue
        files.append(path)
    return files


def require_python_package(import_name: str, install_name: str | None = None) -> None:
    if importlib.util.find_spec(import_name) is None:
        package = install_name or import_name
        raise RuntimeError(
            f"缺少 Python 依赖：{package}\n"
            f"请先运行：{sys.executable} -m pip install -r requirements.txt"
        )


def transcribe_with_whisper(
    audio_dir: Path,
    *,
    model_name: str,
    language: str,
    force: bool,
) -> None:
    require_python_package("whisper", "openai-whisper")
    import whisper  # pylint: disable=import-outside-toplevel

    files = media_files(audio_dir)
    if not files:
        raise RuntimeError(f"在 {audio_dir} 中没有找到音视频文件。")

    model = whisper.load_model(model_name)
    for media_path in files:
        txt_path = media_path.with_suffix(".txt")
        if txt_path.exists() and not force:
            print(f"[Step1] 跳过已有转写：{txt_path.name}")
            continue
        print(f"[Step1] Whisper 转写：{media_path.name}")
        result = model.transcribe(str(media_path), language=language, fp16=False)
        cleaned = clean_transcript(str(result.get("text", "")))
        if not cleaned:
            raise RuntimeError(f"Whisper 没有从 {media_path.name} 识别出可用文字。")
        txt_path.write_text(cleaned + "\n", encoding="utf-8")
        print(f"        -> {txt_path.name}: {cleaned}")


def textgrid_escape(text: str) -> str:
    return text.replace('"', '""')


def detect_audio_duration(path: Path) -> float:
    """Return duration in seconds using soundfile, wave, or ffprobe."""
    try:
        import soundfile as sf  # type: ignore[import-not-found]

        info = sf.info(str(path))
        if info.duration > 0:
            return float(info.duration)
    except Exception:  # pragma: no cover - best-effort optional dependency
        pass

    if path.suffix.lower() == ".wav":
        import wave

        with wave.open(str(path), "rb") as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            if frames > 0 and rate > 0:
                return frames / float(rate)

    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        completed = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return float(completed.stdout.strip())

    raise RuntimeError(
        f"无法读取 {path.name} 的时长。请安装 soundfile 或 ffmpeg/ffprobe，"
        "或者把输入转换为 wav。"
    )


def ensure_mfa_wavs(audio_dir: Path, *, force: bool) -> None:
    """Convert non-wav media to wav so MFA can align it reliably."""
    ffmpeg = shutil.which("ffmpeg")
    for media_path in media_files(audio_dir):
        if media_path.suffix.lower() == ".wav":
            continue
        wav_path = media_path.with_suffix(".wav")
        if wav_path.exists() and not force:
            print(f"[Step2] 跳过已有 MFA wav：{wav_path.name}")
            continue
        if not ffmpeg:
            raise RuntimeError("需要 ffmpeg 把视频/压缩音频转换为 wav，请先安装 ffmpeg。")
        print(f"[Step2] 转换 MFA wav：{media_path.name} -> {wav_path.name}")
        subprocess.run(
            [ffmpeg, "-y", "-i", str(media_path), "-vn", "-ac", "1", "-ar", "16000", str(wav_path)],
            check=True,
        )


def create_seed_textgrids(audio_dir: Path, *, force: bool) -> None:
    """Create MFA seed TextGrids with one utt interval from each transcript."""
    for txt_path in sorted(audio_dir.glob("*.txt")):
        preferred_paths = [txt_path.with_suffix(".wav")] + [
            txt_path.with_suffix(ext) for ext in AUDIO_VIDEO_EXTENSIONS if ext != ".wav"
        ]
        media_path = next((candidate for candidate in preferred_paths if candidate.exists()), None)
        if media_path is None:
            print(f"[Step2] 找不到 {txt_path.name} 对应的音视频，跳过。")
            continue
        textgrid_path = txt_path.with_suffix(".TextGrid")
        if textgrid_path.exists() and not force:
            print(f"[Step2] 跳过已有 TextGrid：{textgrid_path.name}")
            continue
        duration = detect_audio_duration(media_path)
        transcript = txt_path.read_text(encoding="utf-8").strip()
        textgrid = (
            'File type = "ooTextFile"\n'
            'Object class = "TextGrid"\n\n'
            'xmin = 0 \n'
            f'xmax = {duration:.6f} \n'
            'tiers? <exists> \n'
            'size = 1 \n'
            'item []: \n'
            '    item [1]:\n'
            '        class = "IntervalTier" \n'
            '        name = "utt" \n'
            '        xmin = 0 \n'
            f'        xmax = {duration:.6f} \n'
            '        intervals: size = 1 \n'
            '        intervals [1]:\n'
            '            xmin = 0 \n'
            f'            xmax = {duration:.6f} \n'
            f'            text = "{textgrid_escape(transcript)}" \n'
        )
        textgrid_path.write_text(textgrid, encoding="utf-8")
        print(f"[Step2] 生成初始 TextGrid：{textgrid_path.name}")


def run_mfa(
    audio_dir: Path,
    dictionary: Path,
    acoustic_model: Path,
    output_dir: Path,
    *,
    clean: bool,
    extra_args: list[str],
) -> None:
    mfa = shutil.which("mfa")
    if not mfa:
        raise RuntimeError("找不到 mfa 命令。请先安装 Montreal Forced Aligner 并确保 mfa 在 PATH 中。")
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [mfa, "align", str(audio_dir), str(dictionary), str(acoustic_model), str(output_dir)]
    if clean:
        command.append("--clean")
    command.extend(extra_args)
    print("[Step3] 运行 MFA：", " ".join(command))
    subprocess.run(command, check=True)


def convert_mfa_to_pinyin(output_dir: Path, result_dir: Path, *, force: bool) -> None:
    result_dir.mkdir(parents=True, exist_ok=True)
    input_files = sorted(output_dir.rglob("*.TextGrid")) + sorted(output_dir.rglob("*.textgrid"))
    if not input_files:
        raise RuntimeError(f"MFA 输出目录 {output_dir} 中没有 TextGrid 文件。")
    for input_path in input_files:
        relative = input_path.relative_to(output_dir)
        output_path = (result_dir / relative).with_suffix(".TextGrid")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists() and not force:
            print(f"[Step4] 跳过已有结果：{output_path}")
            continue
        generate_pinyin_textgrid(input_path, output_path)
        print(f"[Step4] 输出最终 TextGrid：{output_path}")


def build_parser() -> argparse.ArgumentParser:
    root = repo_root()
    parser = argparse.ArgumentParser(description="音视频批量生成 MFA + 拼音 TextGrid 的一键工具。")
    parser.add_argument("--audio-dir", type=Path, default=root / "audio", help="输入音视频目录")
    parser.add_argument("--output-dir", type=Path, default=root / "output", help="MFA 原始输出目录")
    parser.add_argument("--result-dir", type=Path, default=root / "result", help="最终 TextGrid 输出目录")
    parser.add_argument(
        "--dictionary",
        type=Path,
        default=root / "pretrained_models" / "dictionary" / "mandarin_china_mfa.dict",
        help="MFA 词典路径",
    )
    parser.add_argument(
        "--acoustic-model",
        type=Path,
        default=root / "pretrained_models" / "acoustic" / "mandarin_mfa.zip",
        help="MFA 声学模型路径",
    )
    parser.add_argument("--whisper-model", default="small", help="Whisper 模型名，如 tiny/base/small/medium/large")
    parser.add_argument("--language", default="zh", help="Whisper 语言代码")
    parser.add_argument("--force", action="store_true", help="覆盖已有 txt/TextGrid/result")
    parser.add_argument("--skip-whisper", action="store_true", help="跳过 Step1，直接使用已有 txt")
    parser.add_argument("--skip-mfa", action="store_true", help="跳过 Step3，直接转换已有 output TextGrid")
    parser.add_argument("--mfa-clean", action="store_true", help="给 mfa align 增加 --clean")
    parser.add_argument("--mfa-extra-arg", action="append", default=[], help="追加传给 mfa align 的参数，可重复")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    args.audio_dir.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.result_dir.mkdir(parents=True, exist_ok=True)

    try:
        if not args.skip_whisper:
            transcribe_with_whisper(
                args.audio_dir,
                model_name=args.whisper_model,
                language=args.language,
                force=args.force,
            )
        ensure_mfa_wavs(args.audio_dir, force=args.force)
        create_seed_textgrids(args.audio_dir, force=args.force)
        if not args.skip_mfa:
            run_mfa(
                args.audio_dir,
                args.dictionary,
                args.acoustic_model,
                args.output_dir,
                clean=args.mfa_clean,
                extra_args=args.mfa_extra_arg,
            )
        convert_mfa_to_pinyin(args.output_dir, args.result_dir, force=args.force)
    except Exception as exc:  # noqa: BLE001 - command-line tool should print friendly errors
        print(f"\n出错：{exc}", file=sys.stderr)
        return 1

    print("\n完成！最终 TextGrid 已保存到：", args.result_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

