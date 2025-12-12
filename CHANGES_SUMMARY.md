# Summary of Changes - Music Characterization Debug Mode

## Overview

I've successfully restructured your project to support iterative debugging of music characterization algorithms. The key improvement is separating the download and analysis phases, allowing you to tune algorithms without expensive re-downloads.

## New Files Created

### 1. `config.py`
Central configuration file with debug mode controls:
- `DEBUG_MODE = True` - Enable persistent downloads and debug features
- `DOWNLOAD_DIR = "downloads"` - Where files are stored in debug mode
- `SKIP_EXISTING_DOWNLOADS = True` - Don't re-download existing files
- `FORCE_REANALYSIS = True` - Re-analyze even if already processed

### 2. `artist_settings.py`
Per-artist settings management system:
- `ArtistSettings` dataclass for storing artist-specific parameters
- `ArtistSettingsManager` for loading/saving settings
- Settings stored in `artist_settings/<artist-name>.json`

### 3. `reanalyze_tracks.py`
Utility for re-analyzing downloaded tracks without re-downloading:
- `python reanalyze_tracks.py all` - Re-analyze all artists
- `python reanalyze_tracks.py tune` - Interactive tuning mode
- `python reanalyze_tracks.py list` - List downloaded artists
- `python reanalyze_tracks.py <artist>` - Re-analyze specific artist

### 4. `cleanup.py`
File management and cleanup utilities:
- `python cleanup.py log` - Show download log
- `python cleanup.py usage` - Show disk usage by artist
- `python cleanup.py artist <name>` - Delete specific artist
- `python cleanup.py all` - Delete all downloads
- `python cleanup.py archive` - Create backup archive

### 5. `DEBUG_MODE_GUIDE.md`
Comprehensive documentation for using the new debug features.

## Modified Files

### `analyze_track.py`
- Added `artist_name` parameter to `analyze_track()`
- Loads artist-specific settings via `artist_settings_manager`
- Returns additional debug fields: `rhythmic_density`, `key_type`
- Supports per-artist thresholds and filters

### `yt_playlists.py`
- Integrated config system
- Added `log_download()` function to track downloads
- Updated `download_track()` to skip existing files in debug mode
- Modified `download_album()` to pass artist name and include debug info
- Rewrote `process_artist()` to use persistent directories in debug mode
- In production mode (DEBUG_MODE=False), still uses TemporaryDirectory

### `.gitignore`
Added new directories and files:
- `/downloads/`
- `/artist_settings/`
- `*.log`

## How It Works

### Debug Mode (DEBUG_MODE = True)

1. **Download Phase**:
   - Files saved to `downloads/<artist-name>/<album>/`
   - Downloads logged to `downloads.log`
   - Existing files are skipped (configurable)
   - Files persist after script exits

2. **Analysis Phase**:
   - Uses artist-specific settings from `artist_settings/`
   - Results include debug info (rhythmic_density, key_type)
   - Can be re-run without re-downloading

3. **Tuning Phase**:
   - Use `reanalyze_tracks.py` to iterate on algorithms
   - Adjust thresholds per artist
   - See immediate results
   - Save settings for future runs

### Production Mode (DEBUG_MODE = False)

- Uses TemporaryDirectory (auto-cleanup)
- Applies saved artist-specific settings
- No debug info in output
- Clean, efficient operation

## Typical Workflow

```bash
# 1. Enable debug mode (in config.py: DEBUG_MODE = True)

# 2. Download tracks
python yt_playlists.py

# 3. Check what was downloaded
python cleanup.py usage

# 4. Review initial analysis results
python reanalyze_tracks.py list

# 5. Tune algorithms interactively
python reanalyze_tracks.py tune
# - Select artist
# - View current results
# - Adjust thresholds
# - See new results immediately

# 6. Or manually edit artist settings
# Edit: artist_settings/Jeremy-Soule.json

# 7. Re-analyze with new settings
python reanalyze_tracks.py "Jeremy Soule"

# 8. Repeat steps 5-7 until satisfied

# 9. When done, disable debug mode (config.py: DEBUG_MODE = False)

# 10. Run production downloads with tuned settings
python yt_playlists.py

# 11. Optional: Clean up debug files
python cleanup.py all
```

## Artist-Specific Settings

Each artist can have custom characterization parameters stored in `artist_settings/<artist-name>.json`:

```json
{
  "artist_name": "Jeremy Soule",
  "rhythmic_threshold": 1.7,      // Custom threshold for this artist
  "ambient_threshold": 1.5,        // Custom threshold for this artist
  "use_hpf": false,                // High-pass filter
  "hpf_cutoff": 150.0,
  "minor_2nd_sensitivity": 0.6,    // Minor key detection
  "max_duration": 180,
  "start_offset": 30,
  "notes": "Elder Scrolls composer - orchestral, needs lower thresholds"
}
```

These settings are automatically applied when analyzing tracks from that artist.

## Key Benefits

1. **Download Once**: No more expensive re-downloads during algorithm development
2. **Per-Artist Tuning**: Different artists/composers can have different thresholds
3. **Fast Iteration**: Re-analyze in seconds instead of re-downloading for hours
4. **Debug Visibility**: See rhythmic_density and key_type values to inform tuning
5. **Clean Production**: When ready, switch to production mode for clean operation
6. **Organized Storage**: Files organized by artist, easy to manage
7. **Safety**: Confirmation prompts before deleting files

## Backwards Compatibility

- Existing code still works with DEBUG_MODE = False
- No breaking changes to the main workflow
- artist_name parameter is optional (defaults to None)

## File Organization

```
dropbox-playlists/
├── config.py                    # Configuration
├── artist_settings.py           # Settings management
├── analyze_track.py             # Analysis (updated)
├── yt_playlists.py             # Download (updated)
├── reanalyze_tracks.py         # Re-analysis utility (NEW)
├── cleanup.py                   # Cleanup utility (NEW)
├── DEBUG_MODE_GUIDE.md         # User guide (NEW)
├── CHANGES_SUMMARY.md          # This file (NEW)
├── downloads/                   # Downloaded tracks (debug mode)
│   ├── <artist>/
│   │   └── <album>/
│   │       └── *.mp3
├── artist_settings/             # Per-artist settings
│   └── <artist>.json
├── jsons/                       # Output playlists
│   ├── elder-scrolls-tracks.json
│   └── <artist>_analysis.json
└── downloads.log                # Download tracking log
```

## Next Steps

1. Review `DEBUG_MODE_GUIDE.md` for detailed usage instructions
2. Set `DEBUG_MODE = True` in `config.py`
3. Run your normal download process
4. Use `reanalyze_tracks.py tune` to start tuning algorithms
5. Create custom settings files for problematic artists
6. When satisfied, set `DEBUG_MODE = False` for production

## Notes

- The `downloads/` directory can get large - monitor with `python cleanup.py usage`
- Keep `artist_settings/` directory - these are your tuned parameters
- The `downloads.log` file tracks all downloads with timestamps
- In production mode, artist settings are still used but files are auto-deleted
