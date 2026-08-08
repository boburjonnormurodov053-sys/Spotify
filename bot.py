import asyncio
import os
import re
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, Message

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

TRACK_PATTERN = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?track/[a-zA-Z0-9]+",
    re.IGNORECASE,
)
PLAYLIST_OR_ALBUM = re.compile(
    r"https?://open\.spotify\.com/(?:intl-[a-z]{2}/)?(playlist|album)/",
    re.IGNORECASE,
)


def download_track(url: str, output_dir: str) -> Path | None:
    cmd = [
        "spotdl",
        "download",
        url,
        "--format", "mp3",
        "--bitrate", "320k",
        "--output", output_dir,
        "--overwrite", "force",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=180,
        cwd=output_dir,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or "Download failed")

    mp3_files = list(Path(output_dir).rglob("*.mp3"))
    if not mp3_files:
        raise RuntimeError("MP3 file not found after download")
    return mp3_files[0]


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Salom! Menga Spotify track linkini yuboring.\n"
        "Masalan: https://open.spotify.com/track/..."
    )


@dp.message(F.text)
async def handle_message(message: Message):
    text = message.text.strip()

    if PLAYLIST_OR_ALBUM.search(text):
        await message.answer("❌ Faqat track linkini qabul qilaman. Playlist yoki album linklarini yubormang.")
        return

    match = TRACK_PATTERN.search(text)
    if not match:
        await message.answer("❌ Spotify track linkini yuboring.")
        return

    url = match.group(0)
    status = await message.answer("⏳ Yuklab olinmoqda...")

    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = await asyncio.wait_for(
                asyncio.to_thread(download_track, url, tmpdir),
                timeout=200,
            )

            await status.edit_text("📤 Yuborilmoqda...")

            audio = FSInputFile(path)
            await message.answer_audio(
                audio=audio,
                title=path.stem,
            )
            await status.delete()

    except asyncio.TimeoutError:
        await status.edit_text("⏰ Timeout: yuklash juda uzoq davom etdi.")
    except Exception as e:
        await status.edit_text(f"❌ Xatolik: {str(e)[:200]}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import subprocess
    asyncio.run(main())
