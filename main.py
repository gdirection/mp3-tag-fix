"""
Problem:
- Some downloaded MP3 files have broken ID3 text tags.
- File names look correct, but ID3 Title / Artist / Album may contain mojibake.
- Typical examples:
    "æ€ªæƒ…æ­Œ"       -> "怪情歌"
    "é›¨å‚˜å¿˜äº†å¸¶èµ°" -> "雨傘忘了帶走"
- The likely cause is:
    original UTF-8 bytes were decoded as Latin-1 / ISO-8859-1.
- For this dataset, English text is often already correct.
- We do NOT want to reconstruct tags from file names.
- We only want a dry run:
    * read Title / Artist / Album from ID3
    * try a conservative repair
    * print original value and repaired candidate
    * do NOT write anything back

Repair strategy:
- Skip empty or pure ASCII strings.
- Try:
      repaired = text.encode("latin1").decode("utf-8")
- Accept the repaired value only if:
    * it is different from the original, and
    * it contains target-script characters
      (CJK ranges)
- Otherwise keep the original text unchanged.

Usage:
    python main.py "../"
    python main.py "../some_file.mp3"

Requires:
    mutagen
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from mutagen.id3 import ID3, ID3NoHeaderError


def contains_target_script(text: str) -> bool:
    """Return True if text contains configured target scripts."""
    for ch in text:
        if (
            "\u4e00" <= ch <= "\u9fff" or  # Chinese Han + shared CJK ideographs
            "\u3400" <= ch <= "\u4dbf" or  # CJK Extension A ideographs
            "\u3040" <= ch <= "\u309f" or  # Japanese Hiragana
            "\u30a0" <= ch <= "\u30ff" or  # Japanese Katakana
            "\u3000" <= ch <= "\u303f" or  # Shared CJK punctuation/symbols
            "\uac00" <= ch <= "\ud7af"     # Korean Hangul syllables
        ):
            return True
    return False


def try_repair(text: str) -> str:
    """
    Conservatively repair probable UTF-8-decoded-as-Latin1 mojibake.
    If repair is not convincing, return the original text.
    """
    if not text or text.isascii():
        return text

    try:
        repaired = text.encode("latin1").decode("utf-8")
    except UnicodeError:
        return text

    if repaired != text and contains_target_script(repaired):
        return repaired

    return text


def iter_mp3_files(path: Path) -> Iterable[Path]:
    """Yield one mp3 file or recurse through a directory."""
    if path.is_file():
        if path.suffix.lower() == ".mp3":
            yield path
        return

    for file_path in sorted(path.rglob("*")):
        if file_path.is_file() and file_path.suffix.lower() == ".mp3":
            yield file_path


def read_text_frame(tags: ID3, frame_id: str) -> list[str]:
    """
    Return the list of text values from a text frame.
    If missing or unsupported, return an empty list.
    """
    if frame_id not in tags:
        return []

    frame = tags[frame_id]
    values = getattr(frame, "text", None)
    if not values:
        return []

    return [str(v) for v in values]


def repair_values(values: list[str]) -> tuple[list[str], bool]:
    """Repair a list of text values and report whether any value changed."""
    repaired_values = [try_repair(v) for v in values]
    return repaired_values, repaired_values != values


def print_frame_report(label: str, values: list[str], repaired_values: list[str]) -> bool:
    """
    Print dry-run results for one frame.
    Returns True if any value would change.
    """
    if not values:
        print(f"  {label}: <missing>")
        return False

    any_changed = False
    for idx, (original, repaired) in enumerate(zip(values, repaired_values), start=1):
        changed = repaired != original
        any_changed = any_changed or changed

        print(f"  {label}[{idx}] original: {original}")
        if changed:
            print(f"  {label}[{idx}] fixed   : {repaired}")
        else:
            print(f"  {label}[{idx}] fixed   : <no change>")

    return any_changed


def detect_id3v2_version(mp3_path: Path) -> str | None:
    """Detect the ID3v2 version, if present."""
    try:
        tags = ID3(mp3_path)
        return f"ID3v2.{tags.version[1]}"
    except ID3NoHeaderError:
        return None
    except Exception:
        return None


def update_text_frame(tags: ID3, frame_id: str, values: list[str]) -> None:
    """
    Update a text frame with Unicode-safe encoding.
    - ID3v2.4 supports UTF-8 (encoding=3)
    - ID3v2.3 should use UTF-16 (encoding=1)
    """
    frame = tags[frame_id]
    frame.encoding = 3 if tags.version[1] == 4 else 1
    frame.text = values


def process_file(mp3_path: Path, apply: bool) -> bool:
    """
    Dry-run one mp3 file.
    Returns True if any field would change.
    """
    print(f"\n=== {mp3_path} ===")

    version = detect_id3v2_version(mp3_path)
    if version:
        print(f"  Detected tags: {version}")
    else:
        print("  Detected tags: <none>")

    try:
        tags = ID3(mp3_path)
    except ID3NoHeaderError:
        print("  No ID3v2 tag (skipping TIT2/TPE1/TALB check)")
        return False
    except Exception as exc:
        print(f"  Error reading tag: {exc}")
        return False

    if tags.version[1] == 2:
        print("  ID3v2.2 is unsupported (skipping)")
        return False

    title_values = read_text_frame(tags, "TIT2")
    artist_values = read_text_frame(tags, "TPE1")
    album_values = read_text_frame(tags, "TALB")

    repaired_title, changed_title = repair_values(title_values)
    repaired_artist, changed_artist = repair_values(artist_values)
    repaired_album, changed_album = repair_values(album_values)

    print_frame_report("Title", title_values, repaired_title)
    print_frame_report("Artist", artist_values, repaired_artist)
    print_frame_report("Album", album_values, repaired_album)

    any_changed = changed_title or changed_artist or changed_album
    if not any_changed:
        return False

    if apply:
        if changed_title and "TIT2" in tags:
            update_text_frame(tags, "TIT2", repaired_title)
        if changed_artist and "TPE1" in tags:
            update_text_frame(tags, "TPE1", repaired_artist)
        if changed_album and "TALB" in tags:
            update_text_frame(tags, "TALB", repaired_album)

        try:
            save_v2_version = 3 if tags.version[1] == 3 else 4
            tags.save(mp3_path, v2_version=save_v2_version)
            print("  Applied changes: yes")
        except Exception as exc:
            print(f"  Applied changes: no ({exc})")
            return False
    else:
        print("  Applied changes: no (dry run)")

    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dry-run ID3 mojibake check for MP3 Title/Artist/Album."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to an .mp3 file or a folder containing mp3 files.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write repaired values back to ID3v2 tags. Default is dry run.",
    )
    args = parser.parse_args()

    path = args.path
    if not path.exists():
        raise SystemExit(f"Path does not exist: {path}")

    scanned = 0
    changed = 0

    for mp3_path in iter_mp3_files(path):
        scanned += 1
        if process_file(mp3_path, apply=args.apply):
            changed += 1

    print("\n=== Summary ===")
    print(f"Scanned MP3 files : {scanned}")
    if args.apply:
        print(f"Changed files     : {changed}")
    else:
        print(f"Would change files: {changed}")


if __name__ == "__main__":
    main()
