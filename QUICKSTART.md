# Quick Start Guide

## Getting Started with Debug Mode

### Step 1: Enable Debug Mode

Edit `config.py` and ensure these settings:

```python
DEBUG_MODE = True              # Enable debug features
SKIP_EXISTING_DOWNLOADS = True # Don't re-download existing files
```

### Step 2: Run Initial Download

```bash
python yt_playlists.py
```

This will download tracks to `downloads/<artist>/` and perform initial analysis.

### Step 3: Check What Was Downloaded

```bash
# See disk usage by artist
python cleanup.py usage

# List downloaded artists
python reanalyze_tracks.py list
```

### Step 4: Start Tuning

```bash
# Interactive tuning mode
python reanalyze_tracks.py tune
```

This will:
1. Show you all artists with downloaded tracks
2. Let you select an artist
3. Display current analysis results
4. Allow you to adjust thresholds
5. Show updated results immediately

### Step 5: Iterate

Keep adjusting settings until you're happy with the categorization. Settings are automatically saved to `artist_settings/<artist>.json`.

### Step 6: Production Mode

When satisfied with your tuning:

1. Edit `config.py`: `DEBUG_MODE = False`
2. Run `python yt_playlists.py`
3. Files will use temporary directories (auto-cleanup) but apply your tuned settings

## Key Commands

### Analysis
```bash
python reanalyze_tracks.py all              # Re-analyze all artists
python reanalyze_tracks.py tune             # Interactive tuning
python reanalyze_tracks.py "Jeremy Soule"   # Re-analyze one artist
python reanalyze_tracks.py list             # List artists
```

### Cleanup
```bash
python cleanup.py usage                     # Show disk usage
python cleanup.py log                       # Show download log
python cleanup.py archive                   # Backup downloads
python cleanup.py artist "Jeremy-Soule"     # Delete one artist
python cleanup.py all                       # Delete everything
```

## Understanding the Settings

When you tune an artist, you're adjusting these parameters:

- **rhythmic_threshold** (default: 1.8)
  - Higher values = fewer tracks classified as Combat/Triumph
  - Lower values = more tracks classified as Combat/Triumph
  - Typical range: 1.5 - 2.2

- **ambient_threshold** (default: 1.6)
  - Higher values = more tracks classified as Dark/Light
  - Lower values = fewer tracks classified as Dark/Light
  - Typical range: 1.3 - 1.8

- **minor_2nd_sensitivity** (default: 0.5)
  - Higher values = more tracks detected as Minor key
  - Lower values = fewer tracks detected as Minor key
  - Typical range: 0.3 - 0.8

## Troubleshooting

### Problem: Too many tracks classified as Combat
**Solution**: Increase `rhythmic_threshold` (e.g., from 1.8 to 2.0)

### Problem: Too many tracks classified as Dark/Light
**Solution**: Decrease `ambient_threshold` (e.g., from 1.6 to 1.4)

### Problem: Minor key music classified as Major
**Solution**: Increase `minor_2nd_sensitivity` (e.g., from 0.5 to 0.7)

### Problem: Analysis seems off for certain sections
**Solution**: Adjust `start_offset` and `max_duration` in artist settings

## File Locations

- **Downloaded tracks**: `downloads/<artist>/<album>/*.mp3`
- **Artist settings**: `artist_settings/<artist>.json`
- **Analysis results**: `jsons/<artist>_analysis.json`
- **Download log**: `downloads.log`

## Tips

1. **Start with one artist** - Focus on getting one artist right before moving to others
2. **Look at the numbers** - The debug output shows rhythmic_density values, use these to set thresholds
3. **Similar artists** - If two artists have similar styles, copy settings between them
4. **Document your changes** - Use the "notes" field in settings files to remember why you chose certain values
5. **Back up your settings** - The `artist_settings/` folder is valuable - don't delete it!

## What Gets Cleaned Up?

- `downloads/` - Can be deleted when you're done tuning (run `python cleanup.py all`)
- `jsons/*_analysis.json` - Debug analysis files, can be deleted
- `downloads.log` - Download tracking log, can be deleted

## What to Keep?

- `artist_settings/` - These are your tuned parameters, KEEP these!
- `jsons/elder-scrolls-tracks.json` - Your production playlist output

## Example Session

```bash
# 1. Enable debug mode
# (Edit config.py: DEBUG_MODE = True)

# 2. Download tracks
python yt_playlists.py

# 3. Check disk usage
python cleanup.py usage
# Output: Jeremy-Soule: 45 files, 234.5 MB

# 4. Start interactive tuning
python reanalyze_tracks.py tune
# Select artist: 1
# Current: 20 Combat, 15 Dark, 10 Theme
# Adjust rhythmic_threshold: 1.7
# New: 15 Combat, 18 Dark, 12 Theme
# Better!

# 5. Check another artist
python reanalyze_tracks.py "Brad Derrick"

# 6. When done, switch to production mode
# (Edit config.py: DEBUG_MODE = False)
python yt_playlists.py

# 7. Clean up debug files
python cleanup.py all
```

## Next Steps

Read `DEBUG_MODE_GUIDE.md` for comprehensive documentation of all features.
