# mp3-tag-fix

Dry-run checker for ID3 mojibake in MP3 tags (`TIT2`, `TPE1`, `TALB`).

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
uv run python main.py "../001. HUNTRX, EJAE, AUDREY NUNA, REI AMI, KPop Demon Hunter - Golden.mp3"
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
