import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class VMConfig:
    ffmpeg_bin: str
    ffprobe_bin: str
    assets_dir: Path
    output_dir: Path
    logo_file: str
    bgm_file: str
    outro_file: str
    watermark_crop: str
    logo_position: str
    bgm_volume: float
    target_fps: float

    @classmethod
    def from_env(cls) -> "VMConfig":
        return cls(
            ffmpeg_bin=os.getenv("FFMPEG_BIN", "ffmpeg").strip(),
            ffprobe_bin=os.getenv("FFPROBE_BIN", "ffprobe").strip(),
            assets_dir=Path(os.getenv("ASSETS_DIR", "/opt/sketch_spark_engine/assets")),
            output_dir=Path(os.getenv("OUTPUT_DIR", "/opt/sketch_spark_engine/output")),
            logo_file=os.getenv("LOGO_FILE", "logo_top_left.png").strip(),
            bgm_file=os.getenv("BGM_FILE", "bgm_loop.mp3").strip(),
            outro_file=os.getenv("OUTRO_FILE", "logo_outro.mp4").strip(),
            watermark_crop=os.getenv("WATERMARK_CROP", "iw-240:ih-140:0:0").strip(),
            logo_position=os.getenv("LOGO_POSITION", "20:20").strip(),
            bgm_volume=float(os.getenv("BGM_VOLUME", "0.15")),
            target_fps=float(os.getenv("TARGET_FPS", "30")),
        )

    def asset(self, name: str) -> Path:
        return self.assets_dir / name


def probe(path: Path, cfg: VMConfig) -> dict:
    command = [
        cfg.ffprobe_bin,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(path),
    ]
    data = json.loads(subprocess.check_output(command, text=True))
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError(f"No video stream in {path}")
    audio = next((s for s in data["streams"] if s.get("codec_type") == "audio"), None)
    duration = float(data.get("format", {}).get("duration") or video.get("duration") or 0)
    fps_value = cfg.target_fps
    raw_fps = video.get("avg_frame_rate") or video.get("r_frame_rate") or ""
    try:
        fraction = Fraction(raw_fps)
        if fraction > 0:
            fps_value = float(fraction)
    except (ValueError, ZeroDivisionError):
        pass
    return {
        "width": int(video["width"]),
        "height": int(video["height"]),
        "fps": fps_value,
        "duration": duration,
        "has_audio": audio is not None,
    }


def _run(command: list[str], cwd: Path | None = None, timeout: int = 3600) -> None:
    log.debug("exec: %s", " ".join(command))
    process = subprocess.run(
        command, cwd=str(cwd) if cwd else None, capture_output=True, text=True, timeout=timeout
    )
    if process.returncode != 0:
        raise RuntimeError(
            f"Command failed ({process.returncode}): {' '.join(command[:6])}...\n"
            f"{process.stderr[-4000:]}"
        )


def _fps_text(fps: float) -> str:
    return str(int(fps)) if float(fps).is_integer() else f"{fps:.3f}"


def _encode_args(fps: float) -> list[str]:
    return [
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", _fps_text(fps),
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "48000",
    ]


def _stage_main(raw: Path, voice: Path, logo: Path, bgm: Path, info: dict, cfg: VMConfig, dest: Path) -> None:
    duration = info["duration"]
    filter_complex = (
        f"[0:v]crop={cfg.watermark_crop}[base];"
        f"[base][1:v]overlay={cfg.logo_position}:format=auto[v];"
        f"[2:a]apad[vo];"
        f"[3:a]volume={cfg.bgm_volume}[bgm];"
        f"[bgm][vo]amix=inputs=2:duration=first:normalize=0[mx];"
        f"[mx]atrim=0:{duration:.3f},asetpts=PTS-STARTPTS[a]"
    )
    command = [
        cfg.ffmpeg_bin, "-y",
        "-i", str(raw),
        "-i", str(logo),
        "-i", str(voice),
        "-stream_loop", "-1", "-i", str(bgm),
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "[a]",
        *_encode_args(info["fps"]),
        "-t", f"{duration:.3f}",
        "-movflags", "+faststart",
        str(dest),
    ]
    _run(command)


def _stage_outro(outro_raw: Path, info: dict, cfg: VMConfig, dest: Path) -> None:
    width, height = info["width"], info["height"]
    duration = info["duration"]
    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
        f"fps={_fps_text(info['fps'])}"
    )
    command = [cfg.ffmpeg_bin, "-y", "-i", str(outro_raw)]
    if info["has_audio"]:
        command += [
            "-vf", video_filter,
            "-map", "0:v", "-map", "0:a",
            *_encode_args(info["fps"]),
            "-t", f"{duration:.3f}",
            str(dest),
        ]
    else:
        audio_filter = (
            "anullsrc=channel_layout=stereo:sample_rate=48000,"
            f"atrim=0:{duration:.3f},asetpts=PTS-STARTPTS"
        )
        command += [
            "-filter_complex", f"[0:v]{video_filter}[v];{audio_filter}[a]",
            "-map", "[v]", "-map", "[a]",
            *_encode_args(info["fps"]),
            "-t", f"{duration:.3f}",
            str(dest),
        ]
    _run(command)


def _concat(main: Path, outro: Path, cfg: VMConfig, info: dict, work: Path, dest: Path) -> None:
    list_file = work / "concat.txt"
    list_file.write_text(f"file '{main.name}'\nfile '{outro.name}'\n", encoding="utf-8")
    try:
        _run(
            [
                cfg.ffmpeg_bin, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                "-movflags", "+faststart",
                str(dest),
            ],
            cwd=work,
        )
        return
    except RuntimeError:
        log.warning("Stream-copy concat failed, re-encoding concat instead")
    filter_complex = (
        "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]"
    )
    _run(
        [
            cfg.ffmpeg_bin, "-y",
            "-i", str(main),
            "-i", str(outro),
            "-filter_complex", filter_complex,
            "-map", "[v]", "-map", "[a]",
            *_encode_args(info["fps"]),
            "-movflags", "+faststart",
            str(dest),
        ]
    )


def process_video(
    raw_video_path: str,
    voiceover_path: str,
    output_filename: str,
    cfg: VMConfig | None = None,
) -> Path:
    cfg = cfg or VMConfig.from_env()
    if shutil.which(cfg.ffmpeg_bin) is None and not Path(cfg.ffmpeg_bin).exists():
        raise RuntimeError(f"ffmpeg not found: {cfg.ffmpeg_bin}")

    raw = Path(raw_video_path)
    voice = Path(voiceover_path)
    logo = cfg.asset(cfg.logo_file)
    bgm = cfg.asset(cfg.bgm_file)
    outro_raw = cfg.asset(cfg.outro_file)

    for required in (raw, voice, logo, bgm, outro_raw):
        if not required.is_file():
            raise FileNotFoundError(f"Required input missing: {required}")

    filename = Path(output_filename).name
    final_path = cfg.output_dir / filename
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    started = time.time()
    info = probe(raw, cfg)
    log.info("Source %s | %dx%d @ %.3f fps | %.1fs", raw.name, info["width"], info["height"], info["fps"], info["duration"])

    work = cfg.output_dir / "tmp" / f"{raw.stem}-{int(started)}"
    work.mkdir(parents=True, exist_ok=True)
    main_clip = work / "main.mp4"
    outro_clip = work / "outro.mp4"

    try:
        log.info("Stage 1/3: crop watermark, pin logo, mix voiceover + BGM")
        _stage_main(raw, voice, logo, bgm, info, cfg, main_clip)

        log.info("Stage 2/3: prepare outro slate")
        outro_info = probe(outro_raw, cfg)
        _stage_outro(outro_raw, outro_info, cfg, outro_clip)

        log.info("Stage 3/3: append outro")
        _concat(main_clip, outro_clip, cfg, info, work, final_path)
    except Exception:
        log.exception("Render failed, keeping temp files at %s", work)
        raise

    shutil.rmtree(work, ignore_errors=True)
    log.info("Finished %s in %.1fs", final_path, time.time() - started)
    return final_path
