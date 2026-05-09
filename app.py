import streamlit as st
import tempfile
import subprocess
import zipfile
import re
from pathlib import Path

st.set_page_config(page_title="Video + MP3 Auto Maker", layout="centered")
st.title("🎬 Video + Multiple MP3 Auto Maker")


def clean_filename(name):
    name = Path(name).stem
    name = re.sub(r'[\\/*?:"<>|]', "", name)
    return name.strip()


def time_to_seconds(t):
    parts = t.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + int(s)
    if len(parts) == 2:
        m, s = parts
        return int(m) * 60 + int(s)
    return int(parts[0])


def seconds_to_time(sec):
    sec = int(sec)
    h = sec // 3600
    m = (sec % 3600) // 60
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def get_duration(file_path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def make_video(video_path, audio_path, output_path, start_sec, duration_sec):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-i", str(audio_path),
        "-filter_complex",
        f"[0:v]trim=start={start_sec}:duration={duration_sec},setpts=PTS-STARTPTS,"
        f"scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080[v]",
        "-map", "[v]",
        "-map", "1:a:0",
        "-t", str(duration_sec),
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)


video_file = st.file_uploader("1. Upload Video", type=["mp4", "mov", "mkv"])
start_time = st.text_input("2. Video Start Time", value="00:00:00")
mp3_files = st.file_uploader(
    "3. Upload Multiple MP3 Files",
    type=["mp3", "wav", "m4a"],
    accept_multiple_files=True
)

if st.button("🚀 Export Videos"):
    if not video_file:
        st.error("Please video upload karo.")
    elif not mp3_files:
        st.error("Please MP3 files upload karo.")
    else:
        try:
            start_seconds = time_to_seconds(start_time)

            work_dir = Path(tempfile.mkdtemp())
            input_dir = work_dir / "input"
            output_dir = work_dir / "output"
            input_dir.mkdir()
            output_dir.mkdir()

            video_path = input_dir / video_file.name
            with open(video_path, "wb") as f:
                f.write(video_file.read())

            video_duration = get_duration(video_path)

            current_start = start_seconds
            results = []

            progress = st.progress(0)
            status = st.empty()

            for index, mp3 in enumerate(mp3_files, start=1):
                audio_path = input_dir / mp3.name
                with open(audio_path, "wb") as f:
                    f.write(mp3.read())

                audio_duration = get_duration(audio_path)
                safe_name = clean_filename(mp3.name)
                output_path = output_dir / f"{safe_name}.mp4"

                if current_start + audio_duration > video_duration:
                    st.error("Video length kam pad gayi. Long video upload karo.")
                    break

                status.write(f"Making video: {mp3.name}")

                make_video(
                    video_path=video_path,
                    audio_path=audio_path,
                    output_path=output_path,
                    start_sec=current_start,
                    duration_sec=audio_duration
                )

                end_time = current_start + audio_duration

                with open(output_path, "rb") as f:
                    video_data = f.read()

                results.append({
                    "name": output_path.name,
                    "data": video_data,
                    "video_start": seconds_to_time(current_start),
                    "video_end": seconds_to_time(end_time),
                    "audio_duration": seconds_to_time(audio_duration)
                })

                current_start = end_time
                progress.progress(index / len(mp3_files))

            if results:
                zip_path = work_dir / "all_videos.zip"
                with zipfile.ZipFile(zip_path, "w") as zipf:
                    for item in results:
                        file_path = output_dir / item["name"]
                        zipf.write(file_path, item["name"])

                with open(zip_path, "rb") as f:
                    zip_data = f.read()

                st.session_state["results"] = results
                st.session_state["zip_data"] = zip_data
                st.session_state["final_time"] = seconds_to_time(current_start)

                st.success("✅ All videos exported successfully!")

        except Exception as e:
            st.error(f"Error: {e}")
            st.warning("Check karo FFmpeg properly install hai ya nahi.")


if "results" in st.session_state:
    st.subheader("Download Videos")

    st.download_button(
        label="⬇ Download All Videos ZIP",
        data=st.session_state["zip_data"],
        file_name="all_videos.zip",
        mime="application/zip",
        key="zip_download"
    )

    st.markdown("---")

    for idx, item in enumerate(st.session_state["results"]):
        st.download_button(
            label=f"⬇ Download {item['name']}",
            data=item["data"],
            file_name=item["name"],
            mime="video/mp4",
            key=f"download_{idx}"
        )

        st.write(
            f"Video part used: `{item['video_start']}` to `{item['video_end']}` | "
            f"Audio duration: `{item['audio_duration']}`"
        )

    st.info(f"Final uploaded video used till: {st.session_state['final_time']}")