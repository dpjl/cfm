# CFM (Camera Files Manager) - AI Coding Instructions

## Project Overview

CFM is a Python-based CLI tool for organizing photo/video collections by metadata (camera model, date, etc.) using hard links for zero-disk-usage organization. It includes duplicate detection, ZIP extraction, WhatsApp date correction, file watching, and a React UI for gallery comparison.

**Core Entry Point:** [camerafile/cfm.py](../camerafile/cfm.py) - main CLI with 3 commands: `analyze`, `organize`, `custom`

## Architecture Patterns

### 1. MediaSet: Central Data Structure
The `MediaSet` class ([camerafile/core/MediaSet.py](../camerafile/core/MediaSet.py)) is the backbone - it represents a directory of media files:
- Loads from disk or `.cfm` cache (dump files) for performance
- Contains `media_file_list` (all MediaFile objects), `indexer` (for fast lookups), and `state` (metadata to read)
- Register/unregister methods maintain multiple indexes: `id_map`, `filename_map`, and indexer structures
- Always use `MediaSet.load_media_set()` static method, never instantiate directly

### 2. MediaFile: File Representation
`MediaFile` ([camerafile/core/MediaFile.py](../camerafile/core/MediaFile.py)) wraps a file with:
- `file_desc`: FileDescription (path, size, extension)
- `metadata`: MetadataList with keys like `INTERNAL`, `SIGNATURE`, `CFM_CAMERA_MODEL`, `THUMBNAIL`
- Access dates via `get_date()`, `get_exif_date()`, camera via `get_camera_model()`

### 3. Batch Processing Pattern
All heavy operations use the batch pattern for multiprocessing ([camerafile/processor/](../camerafile/processor/)):
- Extend `CFMBatch` (which extends `TaskWithProgression`)
- Implement `task_getter()` returning a task function, `arguments()` returning list of `BatchElement`
- Examples: `BatchCopy`, `BatchReadInternalMd`, `BatchComputeNecessarySignatures`, `BatchUpdateWhatsAppDates`
- Progress bars are automatic; workers = `Configuration.get().nb_sub_process` (defaults to CPU count)

### 4. Configuration Singleton
`Configuration.get()` ([camerafile/core/Configuration.py](../camerafile/core/Configuration.py)) is the global config singleton:
- Reads from CLI args OR environment variables (e.g., `COMMAND`, `DIR1`, `NB_WORKERS`, `CACHE_PATH`)
- Access via `Configuration.get().nb_sub_process`, `Configuration.get().whatsapp`, etc.
- Must call `Configuration.get().init(args)` once at startup

### 5. Metadata Readers
Metadata extraction uses external tools coordinated by readers in [camerafile/mdtools/](../camerafile/mdtools/):
- **ExifTool** (primary): Singleton process via `ExifTool.execute()` - stays running for performance
- **Internal readers**: JPEGMdReader, AVIMdReader for format-specific extraction
- Metadata flows into `MediaFile.metadata` (a `MetadataList` dict-like object)

## Key Workflows

### Organize Command Flow
```
cfm organize <source> <dest> -f "{date:%Y}/{cm}/{filename}"
  ↓
execute_organize() [cfm.py#193]
  ↓ MediaSet.load_media_set() for source & dest
  ↓ BatchReadInternalMd.execute() - read EXIF in parallel
  ↓ SearchForDuplicates.execute() - compute signatures
  ↓ BatchCopy.execute() - copy/link files to organized structure
  ↓ (if -w3 flag) BatchUpdateWhatsAppDates.execute()
  ↓ (if -w flag) Watcher().start() - continuous monitoring
```

### Watch Mode
The `Watcher` ([camerafile/monitor/Watcher.py](../camerafile/monitor/Watcher.py)) uses `watchdog` to monitor source directory:
- Debounces changes with `sync_delay` (default 60s)
- Reloads destination MediaSet entirely, reprocesses source changes
- Can execute post-processing script via `--post-processing-script` after each sync

### Caching System
CFM caches metadata in `.cfm` folders (or `--cache-path`):
- **Dump files** (`.dill`): Python pickled MediaSet for instant loading
- **SQLite DB** (optional with `-s`): For debugging, NOT used for loading
- Cache invalidation: automatic when files change (tracks modification times)

## File Organization Format
The `--format` flag uses placeholders for organizing files:
- `{date:%Y}` - Year from EXIF date
- `{date:%m}` or `{date:%m[%B]}` - Month as number or `01[January]`
- `{cm}` or `{cm:Unknown}` - Camera model with optional default
- `{filename}` or `{filename:x}` - Original filename, `:x` keeps extension only
- Example: `"{date:%Y}/{date:%m}/{cm}/{filename}"` → `2024/03/Canon_EOS_5D/IMG_1234.jpg`

## WhatsApp Date Correction
Special handling for WhatsApp files ([GUIDE_WHATSAPP_DATE_UPDATE.md](../GUIDE_WHATSAPP_DATE_UPDATE.md)):
- `-w1` / `--whatsapp`: Extract date from filename pattern `IMG-YYYYMMDD-WA####.jpg`
- `-w2 <db>` / `--whatsapp-db`: Use decrypted `msgstore.db` for accurate send/receive dates
- `-w3` / `--whatsapp-date-update`: Actually modify file modification times after copy
- Implementation: `FileAccess.read_whatsapp_info()` extracts, `UpdateWhatsAppDate` task applies

## Copy Modes & Collision Policies
**Copy Modes** (FileAccess.py):
- `HARD_LINK` (default): Zero disk usage, fast, same filesystem required
- `SOFT_LINK`: Symbolic links
- `COPY`: Full file copy (slow, use for cross-filesystem or ZIP extraction)

**Collision Policies** (CopyFile.py):
- `RENAME_PARENT`: Add `~i` to parent directory name
- `RENAME`: Add `~i` to filename
- `SKIP`: Don't copy if exists
- `OVERWRITE`: Replace existing file

## Testing & Development

### Running Tests
```bash
pytest --cov=camerafile tests/
```
Tests in [tests/camerafile/](../tests/camerafile/) cover MediaSet comparisons, organize workflows, duplicates

### Packaging
- Use [tools/create_package.py](../tools/create_package.py) with PyInstaller
- Spec file: [cfm.spec](../cfm.spec)
- Must bundle ExifTool binary (platform-specific in `ext-bin/`)
- Example: `python tools/create_package.py --exiftool /path/to/exiftool --format zip`

### Docker Development
[docker-compose.yml](../docker-compose.yml) example:
```yaml
environment:
  COMMAND: organize
  DIR1: /data/in
  DIR2: /data/out
  ORG_FORMAT: "{date:%Y}/{cm}/{filename}"
  WATCH: true
```

## React UI Integration
The UI ([cfm-ui-41/](../cfm-ui-41/)) is a separate React/Vite project:
- Started with `--ui` flag
- Backend: FastAPI server in [camerafile/api/ManagementApi.py](../camerafile/api/ManagementApi.py)
- Displays side-by-side gallery comparison with duplicate detection results
- Build output bundled into Docker image at `/app/www`

## Common Gotchas

1. **Always use Configuration.get()** - Never create Configuration instances
2. **MediaSet caching** - Changes may not reflect if cache not invalidated; use `--no-dump` to bypass
3. **ExifTool must be initialized** - `Resource.init()` must run before ExifTool calls
4. **Batch task functions** - Must be picklable (no lambdas or local functions)
5. **Logger naming** - Use `LOGGER = Logger(__name__)` not `logging.getLogger()` for consistent formatting
6. **FileAccess abstraction** - Use `StandardFileAccess` vs `ZipFileAccess` depending on source type
7. **Multiprocessing on Windows** - Requires `freeze_support()` in main (already in cfm.py)

## External Dependencies
- **exiftool**: Embedded in `ext-bin/`, extracted at runtime via `Resource.extract_exiftool()`
- **ffmpeg**: Not currently used but referenced in comments
- **dlib**: Face detection (optional feature), predictor model in `data/`

## Extending CFM

### Adding a Custom Processor
1. Create `camerafile/processor/MyProcessor.py` extending `CFMBatch`
2. Implement `task_getter()` and `arguments()`
3. Run via: `cfm custom MyProcessor arg1 arg2`

### Adding Metadata Type
1. Add constant to [camerafile/core/Constants.py](../camerafile/core/Constants.py)
2. Add to `MetadataList.__init__()` in [metadata/MetadataList.py](../camerafile/metadata/MetadataList.py)
3. Create reader/writer in `camerafile/mdtools/` or `camerafile/metadata/`
