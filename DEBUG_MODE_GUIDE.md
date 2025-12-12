# Debug Mode and Algorithm Tuning Guide

## Overview

The project now supports a **DEBUG_MODE** that separates the download and analysis phases, allowing you to:

1. Download tracks once and keep them for testing
2. Iterate on characterization algorithms without re-downloading
3. Store per-artist settings to tune algorithms for different musical styles
4. Track downloaded files for manual cleanup

## Configuration

Edit `config.py` to control behavior:

```python
DEBUG_MODE = True              # Enable debug features
DOWNLOAD_DIR = "downloads"     # Where to store downloaded files
SKIP_EXISTING_DOWNLOADS = True # Don't re-download existing files
FORCE_REANALYSIS = True        # Re-analyze even if already processed
```

### Production vs Debug Mode

**Debug Mode (DEBUG_MODE = True)**:
- Downloads are saved to `downloads/` directory (persistent)
- Files are organized by artist
- Downloads are logged to `downloads.log`
- Analysis results include extra debugging info (rhythmic_density, key_type)
- Existing files are skipped if `SKIP_EXISTING_DOWNLOADS = True`

**Production Mode (DEBUG_MODE = False)**:
- Downloads use temporary directories (auto-deleted after processing)
- Analysis and deletion happen immediately
- No download logs
- Clean output files without debug info

## Per-Artist Settings

Each artist can have custom characterization settings stored in `artist_settings/<artist-name>.json`:

```json
{
  "artist_name": "Jeremy Soule",
  "rhythmic_threshold": 1.8,
  "ambient_threshold": 1.6,
  "use_hpf": false,
  "hpf_cutoff": 150.0,
  "minor_2nd_sensitivity": 0.5,
  "max_duration": 180,
  "start_offset": 30,
  "notes": "Elder Scrolls composer - needs lower thresholds"
}
```

### Settings Explanation

- **rhythmic_threshold**: Values above this are classified as "Rhythmic" (Combat/Triumph)
- **ambient_threshold**: Values below this are classified as "Ambient" (Dark/Light)
- **use_hpf**: Apply high-pass filter to remove low frequencies
- **hpf_cutoff**: Frequency cutoff for high-pass filter (Hz)
- **minor_2nd_sensitivity**: Sensitivity for detecting minor keys (0.0-1.0)
- **max_duration**: Maximum seconds to analyze from a track
- **start_offset**: Where to start analysis in the track (seconds)

## Workflow for Tuning Algorithms

### Step 1: Initial Download

With `DEBUG_MODE = True`, run your normal download process:

```bash
python yt_playlists.py
```

This will:
- Download tracks to `downloads/<artist-name>/`
- Log downloads to `downloads.log`
- Perform initial analysis with default settings
- Save results to `jsons/`

### Step 2: Review Results

Check the generated JSON files to see how tracks were categorized:

```bash
# View mood distribution
python reanalyze_tracks.py list
```

### Step 3: Re-analyze with Different Settings

Re-analyze existing downloads without re-downloading:

```bash
# Re-analyze all artists
python reanalyze_tracks.py all

# Re-analyze specific artist
python reanalyze_tracks.py "Jeremy Soule"

# Interactive tuning mode
python reanalyze_tracks.py tune
```

### Step 4: Tune Settings Interactively

The interactive tuning mode (`tune`) will:
1. Show you all downloaded artists
2. Let you select an artist
3. Display current settings and analysis results
4. Allow you to adjust thresholds
5. Immediately re-analyze and show new results

Example session:
```
Available artists:
  1. Jeremy Soule (45 tracks)
  2. Brad Derrick (23 tracks)

Select artist number: 1

Current settings for Jeremy Soule:
  Rhythmic threshold: 1.8
  Ambient threshold: 1.6
  Minor 2nd sensitivity: 0.5

Analysis Summary:
  Combat: 15 (33.3%)
  Dark: 20 (44.4%)
  Theme: 10 (22.2%)

Rhythmic density range:
  Min: 0.845
  Max: 2.134
  Avg: 1.423

Adjust settings? (y/n): y
Rhythmic threshold [1.8]: 1.7
Ambient threshold [1.6]: 1.5
Minor 2nd sensitivity [0.5]: 0.6

Settings saved. Re-analyzing...
[New results displayed]
```

### Step 5: Create Custom Settings Files

Manually create/edit settings files for fine-tuned control:

1. Create `artist_settings/<artist-name>.json`
2. Adjust parameters based on the artist's style
3. Re-run analysis: `python reanalyze_tracks.py "<artist-name>"`

### Step 6: When Ready for Production

Once you're satisfied with the settings:

1. Set `DEBUG_MODE = False` in `config.py`
2. Run the download process - it will:
   - Use temporary directories (auto-cleanup)
   - Apply your custom per-artist settings
   - Generate clean output without debug info

## File Organization

```
dropbox-playlists/
├── config.py                    # Main configuration
├── artist_settings.py           # Settings management
├── analyze_track.py             # Analysis engine (updated)
├── yt_playlists.py             # Download & process (updated)
├── reanalyze_tracks.py         # Re-analysis utility (NEW)
├── downloads/                   # Downloaded tracks (debug mode)
│   ├── Jeremy-Soule/
│   │   ├── Album-Name/
│   │   │   ├── track1.mp3
│   │   │   └── track2.mp3
│   └── Brad-Derrick/
├── artist_settings/             # Per-artist settings
│   ├── Jeremy-Soule.json
│   └── Brad-Derrick.json
├── jsons/                       # Output playlists
│   ├── elder-scrolls-tracks.json
│   ├── Jeremy-Soule_analysis.json
│   └── Brad-Derrick_analysis.json
└── downloads.log                # Download log (debug mode)
```

## Manual Cleanup

When you're done tuning and want to clean up:

```bash
# Check what was downloaded
type downloads.log

# Remove all downloads
rmdir /s downloads

# Remove analysis results
rmdir /s jsons

# Keep artist settings for future use
# (don't delete artist_settings/)
```

## Tips for Algorithm Tuning

1. **Start with defaults**: Run initial analysis to see baseline results
2. **Focus on one artist at a time**: Each artist/composer has unique characteristics
3. **Look at outliers**: Check tracks that are mis-categorized
4. **Use rhythmic_density ranges**: The debug info shows min/max/avg - use these to set thresholds
5. **Iterate quickly**: With existing downloads, re-analysis is fast
6. **Document your findings**: Use the "notes" field in settings files
7. **Compare similar artists**: If two artists should behave similarly, copy settings

## Common Adjustments

### Artist produces mostly ambient music (e.g., film scores)
- Lower both thresholds: `rhythmic_threshold: 1.6`, `ambient_threshold: 1.4`

### Artist has heavy percussion that's misclassified
- Raise `rhythmic_threshold` to 2.0 or higher
- Try enabling high-pass filter: `use_hpf: true`

### Minor keys are being detected as Major
- Increase `minor_2nd_sensitivity` to 0.7 or 0.8

### Tracks are too long/short for good analysis
- Adjust `max_duration` (default: 180 seconds)
- Adjust `start_offset` (default: 30 seconds)
