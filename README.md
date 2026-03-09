# mp3-tag-fix

ID3v2 mojibake detector for MP3 tags (`TIT2`, `TPE1`, `TALB`), with dry run by default and optional apply mode.

## Purpose

This tool targets a specific mojibake pattern in ID3v2 text frames:

- likely-broken text pattern: UTF-8 bytes decoded as Latin-1
- repair attempt: `text.encode("latin1").decode("utf-8")`
- focus: CJK-heavy music libraries (Chinese/Japanese/Korean metadata)

## Limitations

- Repair acceptance is conservative: a candidate is accepted only when it
  contains CJK script characters (Han/Hiragana/Katakana/Hangul).
- Non-CJK mojibake (for example `Ãbermensch` -> `Übermensch`) is intentionally
  not auto-accepted by current logic.
- The tool checks ID3v2 frames only (`TIT2`, `TPE1`, `TALB`), not ID3v1 fields.
- ID3v2.2 files are skipped (the tool supports processing/apply for v2.3/v2.4).
- This is not a general language detection or universal encoding repair tool.
- `--apply` writes only fields that pass the acceptance rule; default mode is
  dry run (no file changes).

## Setup

```bash
uv sync
```

## Run (recommended)

From the `mp3-tag-fix/` directory, your MP3 files are one level up:

```bash
uv run python main.py "../"
```

Single file:

```bash
uv run python main.py "../some_file.mp3"
```

## Alternative (activate venv first)

```bash
source .venv/bin/activate
python main.py "../"
```

## Apply changes (write to ID3v2 tags)

Dry run is the default. Add `--apply` to save repaired values:

```bash
uv run python main.py "../" --apply
```
