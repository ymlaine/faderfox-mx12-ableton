# Changelog

All notable changes to the Faderfox MX12 Control Surface will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2025-01-12

### Added
- **Smart page filling system**: |1-|8 tracks fill pages first, then | tracks fill remaining slots
- **|0 = | equivalence**: Tracks with |0 suffix treated as | (filler group)
- **Fallback mode**: If no |x tracks, fill all 8 pages with | tracks only
- **Scroll depth indicator**: LEDs fill right-to-left showing scroll position from start
- **Visual feedback**: 2-second LED display (1 LED = 1 track scrolled, max 12)

### Changed
- **BREAKING**: Track marker changed from `%` to `|` for better visibility
- **BREAKING**: Complete refactor of page organization system
- Pages now filled intelligently based on track suffixes
- | tracks distributed across pages in order of appearance
- Page positioning system using `_page_start_positions` for accurate overflow handling

### Fixed
- LED persistence when switching display modes
- LEDs not updating during scroll indicator display
- LEDs remaining lit in LOCKS mode
- Scroll indicator direction bug (now shows depth from start, not left/right)
- Page overflow bug where tracks with >12 items appeared on next page

## [2.9.x] - Development Versions

### [2.9.9] - 2025-01-11
- Improved scroll indicator with 1 LED = 1 hidden track
- Directional display (left/right)

### [2.9.8] - 2025-01-11
- Fixed LED updates in scroll indicator and LOCKS mode
- Force MIDI send (ignore cache) for clean display

### [2.9.7] - 2025-01-11
- Fixed LED persistence on mode switch
- Added visual scroll position indicator (2-second display)

### [2.9.6] - 2025-01-11
- Support for absolute encoder mode (0-127)
- Direction detection from value changes

### [2.9.5] - 2025-01-11
- Differentiated LED blink patterns
  - FAST BLINK (2.5Hz): Virtual page tracks not on current page
  - SLOW BLINK (1Hz): Virtual page + current page button (double function)

### [2.9.4] - 2025-01-10
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
- Multi-page organization (|0-|8)
- Track locking system
- Preview mode
- Activity LED monitoring (polling-based)

---

## Migration Notes

### 3.0.0 Migration
**Track organization has changed**. If you upgrade from 2.x:
1. Check track suffixes (use |1-|8 for dedicated pages, | for fillers)
2. Pages will reorganize on next script load
3. Locked tracks (virtual page) are preserved

### 2.0.0 Migration
**Architecture changed from polling to listeners**:
1. Audio tracks: Add `|` suffix for automatic VU monitoring
2. MIDI tracks: Add M4L device `MX12byYVMA.amxd`
3. Performance improvement: ~99% less MIDI traffic

---

For detailed usage, see [README.md](README.md).
