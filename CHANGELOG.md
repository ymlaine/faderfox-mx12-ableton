# Changelog

All notable changes to the Faderfox MX12 Control Surface will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-11-12

### Added
- **Smart page filling system**: |1-|8 tracks fill pages first, then | tracks fill remaining slots
- **Fallback mode**: If no |x tracks, fill all 8 pages with | tracks only
- **Scroll depth indicator**: LEDs fill right-to-left showing scroll position from start
- **Visual feedback**: 2-second LED display (1 LED = 1 track scrolled, max 12)

### Changed
- **BREAKING**: Track marker changed from `%` to `|` for better visibility
- **BREAKING**: Complete refactor of page organization system
- **BREAKING**: Renamed "LOCKS" terminology to "PINS" for better clarity
  - Virtual page mode now called "PINS mode" (was "LOCKS mode")
  - Track pinning/unpinning (was lock/unlock)
  - `_pinned_tracks` variable (was `_locked_tracks`)
  - More intuitive terminology: "pin a track" vs "lock a track"
- **BREAKING**: Removed `|0` suffix support (use `|` instead)
  - Simplified track naming: only `|` and `|1` to `|8` are valid
  - `|0` no longer recognized as equivalent to `|`
- Pages now filled intelligently based on track suffixes
- | tracks distributed across pages in order of appearance
- Page positioning system using `_page_start_positions` for accurate overflow handling

### Fixed
- LED persistence when switching display modes
- LEDs not updating during scroll indicator display
- LEDs remaining lit in PINS mode
- Scroll indicator direction bug (now shows depth from start, not left/right)
- Page overflow bug where tracks with >12 items appeared on next page

## [2.9.x] - Development Versions

### [2.9.9] - 2025-11-11
- Improved scroll indicator with 1 LED = 1 hidden track
- Directional display (left/right)

### [2.9.8] - 2025-11-11
- Fixed LED updates in scroll indicator and LOCKS mode
- Force MIDI send (ignore cache) for clean display

### [2.9.7] - 2025-11-11
- Fixed LED persistence on mode switch
- Added visual scroll position indicator (2-second display)

### [2.9.6] - 2025-11-11
- Support for absolute encoder mode (0-127)
- Direction detection from value changes

### [2.9.5] - 2025-11-11
- Differentiated LED blink patterns
  - FAST BLINK (2.5Hz): Pinned tracks not on current page
  - SLOW BLINK (1Hz): Pinned track + current page button (double function)

### [2.9.4] - 2025-11-10
- Virtual page membership LED indicator in PAGE mode

## [2.6.0] - Earlier

### Added
- SHIFT+CC45 recording control with LED indicator
- Config system for listener suspend/resume
- Prevents callback flood during parameter changes

### Changed
- SHIFT system architecture: CC47 as modifier button

## [2.5.1] - Earlier

### Added
- Config system for listener management
- Listener suspend/resume during parameter sync

### Fixed
- Callback flood prevention during parameter updates

## [2.0.0] - Earlier

### Added
- Listener-based activity detection (replacing polling)
- VU meter listeners for audio tracks
- M4L device parameter listeners for MIDI tracks
- Bidirectional parameter feedback
- State tracking to reduce MIDI traffic (99% reduction)

### Changed
- **BREAKING**: Switched from polling to listener architecture
- Significant performance improvements

## [1.x] - Initial Versions

### Added
- Initial Faderfox MX12 support
- Basic rack device mapping (Macro 1-3)
- Multi-page organization (|1-|8)
- Track pinning system (virtual page)
- Preview mode
- Activity LED monitoring (polling-based)

---

## Migration Notes

### 3.0.0 Migration
**Track organization and terminology have changed**. If you upgrade from 2.x:
1. **Terminology change**: "LOCKS" → "PINS"
   - Virtual page mode is now called "PINS mode"
   - CC 45 button is now "PIN" button (was "LOCK")
   - Track collections are "pinned" (was "locked")
   - Pinned tracks are preserved during upgrade
2. **Track suffixes**: Use |1-|8 for dedicated pages, | for fillers
   - **IMPORTANT**: `|0` is no longer supported, rename to `|`
3. Pages will reorganize on next script load based on new smart filling system

### 2.0.0 Migration
**Architecture changed from polling to listeners**:
1. Audio tracks: Add `|` suffix for automatic VU monitoring
2. MIDI tracks: Add M4L device `MX12byYVMA.amxd`
3. Performance improvement: ~99% less MIDI traffic

---

For detailed usage, see [README.md](README.md).
