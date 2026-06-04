from __future__ import annotations

import math
import shutil
import subprocess
from pathlib import Path


PROJECT = Path(__file__).resolve().parent
ASSET_ROOT = PROJECT / "assets"
EXPORTS = PROJECT / "exports"
WORK_ROOT = EXPORTS / "work_clips"
SNAPSHOT_ROOT = EXPORTS / "render_snapshot"
CAPTION_ROOT = EXPORTS / "caption_overlays"
FONT = Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf")
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
SWIFT = shutil.which("swift") or "/usr/bin/swift"
MUSIC = ASSET_ROOT / (
    "Standing%20EGG%20-%20Little%20Star%20_%20%EB%A6%AC%ED%8B%80%EC%8A%A4%ED%83%80%20"
    "[dI8NZsjRyGk].mp3"
)

SECTIONS = [
    "00_opening",
    "01_birth_newborn",
    "02_1-3_months",
    "03_4-6_months",
    "04_7-9_months",
    "05_10-12_months",
    "06_family_ending",
]

CAPTIONS = {
    "00_opening": ["우리에게 와줘서 고마워", "너의 첫 번째 생일을 축하해"],
    "01_birth_newborn": ["아주 작고 소중했던 첫 만남", "처음 품에 안은 그 순간을 잊지 않을게"],
    "02_1-3_months": ["하루하루 조금씩 자라던 시간", "너의 작은 미소가 우리 집을 환하게 밝혔어"],
    "03_4-6_months": ["웃음도 표정도 점점 많아지고", "세상이 궁금해지기 시작한 너"],
    "04_7-9_months": ["앉고, 기고, 더 멀리 나아가던 날들", "너의 모든 처음이 우리에겐 선물이었어"],
    "05_10-12_months": ["어느새 이렇게 크게 자라서", "너만의 속도로 멋지게 세상을 만나고 있어"],
    "06_family_ending": ["첫 번째 생일을 진심으로 축하해", "윤서야 사랑해"],
}

MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".mp4"}
PHOTO_EXTS = {".jpg", ".jpeg", ".png"}


def shell(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def ffmpeg_text_escape(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace(":", r"\:")
        .replace("'", r"\'")
        .replace(",", r"\,")
        .replace("[", r"\[")
        .replace("]", r"\]")
    )


def section_media(section: str) -> list[Path]:
    section_dir = ASSET_ROOT / section
    return [
        p
        for p in sorted(section_dir.iterdir())
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS
    ]


def build_snapshot() -> dict[str, list[Path]]:
    if SNAPSHOT_ROOT.exists():
        shutil.rmtree(SNAPSHOT_ROOT)
    SNAPSHOT_ROOT.mkdir(parents=True)
    snapshot: dict[str, list[Path]] = {}
    for section in SECTIONS:
        files = section_media(section)
        dst_dir = SNAPSHOT_ROOT / section
        dst_dir.mkdir()
        copied: list[Path] = []
        for src in files:
            dst = dst_dir / src.name
            shutil.copy2(src, dst)
            copied.append(dst)
        snapshot[section] = copied
    return snapshot


def caption_indexes(count: int) -> tuple[int, int]:
    if count <= 1:
        return (0, 0)
    first = max(0, math.floor(count * 0.2))
    second = min(count - 1, math.floor(count * 0.68))
    if second == first:
        second = min(count - 1, first + 1)
    return first, second


def photo_filter(duration: float, text: str | None) -> str:
    base = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,"
        "format=yuv420p,"
        "fade=t=in:st=0:d=0.30,"
        f"fade=t=out:st={duration - 0.35:.2f}:d=0.35"
    )
    return base


def video_filter(duration: float, text: str | None) -> str:
    base = (
        "scale=1920:1080:force_original_aspect_ratio=decrease,"
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,"
        "format=yuv420p,"
        "fade=t=in:st=0:d=0.25,"
        f"fade=t=out:st={duration - 0.30:.2f}:d=0.30"
    )
    return base


def ensure_caption_png(text: str, slug: str) -> Path:
    CAPTION_ROOT.mkdir(parents=True, exist_ok=True)
    out = CAPTION_ROOT / f"{slug}.png"
    if out.exists():
        return out
    shell([SWIFT, str(PROJECT / "render_caption.swift"), str(out), text])
    return out


def render_standard_section_clips(snapshot: dict[str, list[Path]]) -> list[Path]:
    if WORK_ROOT.exists():
        for clip in WORK_ROOT.glob("*.mp4"):
            clip.unlink()
    else:
        WORK_ROOT.mkdir(parents=True)

    clip_paths: list[Path] = []
    clip_index = 1
    for section in SECTIONS[:-1]:
        media = snapshot[section]
        first_idx, second_idx = caption_indexes(len(media))
        section_captions = CAPTIONS[section]
        caption_map = {
            first_idx: section_captions[0],
            second_idx: section_captions[1],
        }
        for idx, media_path in enumerate(media):
            duration = 3.4 if media_path.suffix.lower() in PHOTO_EXTS else 4.2
            out = WORK_ROOT / f"clip_{clip_index:03d}.mp4"
            text = caption_map.get(idx)
            caption_png = ensure_caption_png(text, f"{section}_{idx:03d}") if text else None
            if media_path.suffix.lower() in PHOTO_EXTS:
                if caption_png:
                    cmd = [
                        FFMPEG,
                        "-y",
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-loop",
                        "1",
                        "-t",
                        f"{duration:.2f}",
                        "-i",
                        str(media_path),
                        "-loop",
                        "1",
                        "-t",
                        f"{duration:.2f}",
                        "-i",
                        str(caption_png),
                        "-filter_complex",
                        (
                            f"[0:v]{photo_filter(duration, None)}[base];"
                            "[1:v]format=rgba[cap];"
                            "[base][cap]overlay=0:0:shortest=1[vout]"
                        ),
                        "-map",
                        "[vout]",
                        "-r",
                        "30",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "22",
                        "-an",
                        str(out),
                    ]
                else:
                    cmd = [
                        FFMPEG,
                        "-y",
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-loop",
                        "1",
                        "-t",
                        f"{duration:.2f}",
                        "-i",
                        str(media_path),
                        "-vf",
                        photo_filter(duration, None),
                        "-r",
                        "30",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "22",
                        "-an",
                        str(out),
                    ]
            else:
                if caption_png:
                    cmd = [
                        FFMPEG,
                        "-y",
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        str(media_path),
                        "-loop",
                        "1",
                        "-t",
                        f"{duration:.2f}",
                        "-i",
                        str(caption_png),
                        "-t",
                        f"{duration:.2f}",
                        "-filter_complex",
                        (
                            f"[0:v]{video_filter(duration, None)}[base];"
                            "[1:v]format=rgba[cap];"
                            "[base][cap]overlay=0:0:shortest=1[vout]"
                        ),
                        "-map",
                        "[vout]",
                        "-r",
                        "30",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-an",
                        str(out),
                    ]
                else:
                    cmd = [
                        FFMPEG,
                        "-y",
                        "-nostdin",
                        "-hide_banner",
                        "-loglevel",
                        "error",
                        "-i",
                        str(media_path),
                        "-t",
                        f"{duration:.2f}",
                        "-vf",
                        video_filter(duration, None),
                        "-r",
                        "30",
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "23",
                        "-an",
                        str(out),
                    ]
            shell(cmd)
            clip_paths.append(out)
            clip_index += 1
    return clip_paths


def render_family_ending(snapshot: dict[str, list[Path]]) -> Path:
    ending_files = snapshot["06_family_ending"]
    duration = max(14.0, 2.2 * len(ending_files) + 3.5)
    out = WORK_ROOT / "clip_family_ending.mp4"
    early_caption_png = ensure_caption_png(CAPTIONS["06_family_ending"][0], "family_ending_early")
    final_caption_png = ensure_caption_png(CAPTIONS["06_family_ending"][1], "family_ending_final")

    cmd = [
        FFMPEG,
        "-y",
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-t",
        f"{duration:.2f}",
        "-i",
        "color=c=0x111111:s=1920x1080:r=30",
    ]
    for photo in ending_files:
        cmd.extend(["-loop", "1", "-t", f"{duration:.2f}", "-i", str(photo)])
    cmd.extend(["-loop", "1", "-t", f"{duration:.2f}", "-i", str(early_caption_png)])
    cmd.extend(["-loop", "1", "-t", f"{duration:.2f}", "-i", str(final_caption_png)])

    positions = [
        (-140, -70),
        (110, -40),
        (-60, 110),
        (170, 100),
        (0, 20),
        (-180, 55),
        (150, -110),
    ]

    filters: list[str] = []
    filters.append("[0:v]format=rgba[bg0]")

    for idx in range(len(ending_files)):
        label = f"p{idx}"
        angle = (-4 + idx * 2.0) * math.pi / 180.0
        filters.append(
            f"[{idx + 1}:v]"
            "scale=720:540:force_original_aspect_ratio=decrease,"
            "pad=770:590:(ow-iw)/2:(oh-ih)/2:color=white,"
            "format=rgba,"
            f"rotate={angle:.6f}:ow=rotw({angle:.6f}):oh=roth({angle:.6f}):c=none"
            f"[{label}]"
        )

    current = "bg0"
    for idx in range(len(ending_files)):
        next_label = f"bg{idx + 1}"
        photo_label = f"p{idx}"
        start = 0.8 + idx * 1.25
        move = 0.55
        dx, dy = positions[idx % len(positions)]
        target_x = f"(W-w)/2{dx:+d}"
        target_y = f"(H-h)/2{dy:+d}"
        start_x = "(W-w)/2"
        start_y = "(H-h)/2+120"
        x_expr = (
            f"if(lt(t,{start:.2f}),NAN,"
            f"if(lt(t,{start + move:.2f}),"
            f"{start_x}+(({target_x})-({start_x}))*((t-{start:.2f})/{move:.2f}),"
            f"{target_x}))"
        )
        y_expr = (
            f"if(lt(t,{start:.2f}),NAN,"
            f"if(lt(t,{start + move:.2f}),"
            f"{start_y}+(({target_y})-({start_y}))*((t-{start:.2f})/{move:.2f}),"
            f"{target_y}))"
        )
        filters.append(
            f"[{current}][{photo_label}]overlay="
            f"x='{x_expr}':y='{y_expr}':shortest=1[{next_label}]"
        )
        current = next_label

    first_caption_start = max(0.8, duration - 7.2)
    first_caption_end = duration - 3.7
    final_caption_start = duration - 3.1
    early_label = f"{len(ending_files) + 1}:v"
    final_label = f"{len(ending_files) + 2}:v"
    filters.append(
        f"[{early_label}]format=rgba[earlycap]"
    )
    filters.append(
        f"[{final_label}]format=rgba[finalcap]"
    )
    filters.append(
        f"[{current}][earlycap]overlay=0:0:enable='between(t,{first_caption_start:.2f},{first_caption_end:.2f})'[cap1]"
    )
    filters.append(
        f"[cap1][finalcap]overlay=0:0:enable='gte(t,{final_caption_start:.2f})'[vout]"
    )

    cmd.extend(
        [
            "-filter_complex",
            ";".join(filters),
            "-map",
            "[vout]",
            "-r",
            "30",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "22",
            "-an",
            str(out),
        ]
    )
    shell(cmd)
    return out


def concat_clips(clips: list[Path]) -> Path:
    concat_file = WORK_ROOT / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{clip.as_posix()}'\n" for clip in clips),
        encoding="utf-8",
    )
    silent = EXPORTS / "yunseo_growth_video_latest_silent.mp4"
    shell(
        [
            FFMPEG,
            "-y",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(silent),
        ]
    )
    return silent


def probe_duration(path: Path) -> float:
    output = subprocess.check_output(
        [
            FFPROBE,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    ).strip()
    return float(output)


def add_music(silent: Path) -> tuple[Path, Path]:
    duration = probe_duration(silent)
    fade_start = max(0.0, duration - 6.0)
    with_music = EXPORTS / "yunseo_growth_video_latest_with_music.mp4"
    discord = EXPORTS / "yunseo_growth_video_latest_discord.mp4"
    shell(
        [
            FFMPEG,
            "-y",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(silent),
            "-stream_loop",
            "-1",
            "-i",
            str(MUSIC),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-af",
            f"atrim=0:{duration:.3f},asetpts=N/SR/TB,afade=t=out:st={fade_start:.3f}:d=6",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(with_music),
        ]
    )
    shell(
        [
            FFMPEG,
            "-y",
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(with_music),
            "-vf",
            "scale=1280:720:force_original_aspect_ratio=decrease,"
            "pad=1280:720:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "26",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(discord),
        ]
    )
    return with_music, discord


def main() -> None:
    snapshot = build_snapshot()
    total_media = sum(len(snapshot[section]) for section in SECTIONS)
    print(f"snapshot media: {total_media}", flush=True)
    standard_clips = render_standard_section_clips(snapshot)
    ending_clip = render_family_ending(snapshot)
    silent = concat_clips(standard_clips + [ending_clip])
    with_music, discord = add_music(silent)
    print(f"silent={silent}", flush=True)
    print(f"with_music={with_music}", flush=True)
    print(f"discord={discord}", flush=True)


if __name__ == "__main__":
    main()
