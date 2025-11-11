# Faderfox MX12 Control Surface for Ableton Live

A professional Ableton Live Remote Script for the Faderfox MX12 MIDI controller, providing deep integration with rack devices, multi-page organization, and advanced workflow features.

**Version:** 3.0.0
**Author:** Yves-Marie LAINÉ
**License:** Creative Commons Attribution 4.0 International (CC BY 4.0)

---

## 🎯 Features

### Core Functionality
- **Automatic Rack Mapping**: Faders and knobs automatically map to the first rack device on each track
  - Fader → Macro 1
  - Top Pot → Macro 2
  - Bottom Pot → Macro 3
- **Bidirectional Feedback**: Hardware and software stay in sync
- **Pickup Mode**: Prevents parameter jumps when moving controls

### Organization System
- **Smart Page System**: Organize tracks with `%1` to `%8` suffixes
- **Flexible Filling**: Generic `%` tracks fill empty slots automatically
- **8 Pages × 12 Tracks**: Up to 96 tracks accessible
- **Virtual Page (LOCKS)**: Create custom track collections across pages

### Workflow Features
- **Track Locking**: Keep important tracks visible across page changes
- **Scroll Indicator**: Visual feedback showing hidden tracks (2-second display)
- **Preview Mode**: Try parameter changes, instantly revert
- **Recording Control**: Quick recording start/stop with LED indicator
- **Activity LEDs**: Real-time audio/MIDI activity monitoring

---

## 🎛️ Controller Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                     FADERFOX MX12 CONTROL SURFACE                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [ENCODER] CC 60  ← Scroll through tracks                           │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  TOP POTS (CC 0-11)      →  Macro 2                          │   │
│  │  [ 0 ][ 1 ][ 2 ][ 3 ][ 4 ][ 5 ][ 6 ][ 7 ][ 8 ][ 9 ][10][11] │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  BOTTOM POTS (CC 12-23)  →  Macro 3                          │   │
│  │  [12][13][14][15][16][17][18][19][20][21][22][23]            │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  FADERS (CC 48-59)       →  Macro 1                          │   │
│  │  [48][49][50][51][52][53][54][55][56][57][58][59]            │   │
│  │   │  │  │  │  │  │  │  │  │  │  │  │                         │   │
│  │   ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼  ▼                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  RED BUTTONS (CC 24-35) + Activity LEDs                       │   │
│  │  [🔴][🔴][🔴][🔴][🔴][🔴][🔴][🔴][🔴][🔴][🔴][🔴]           │   │
│  │   0   1   2   3   4   5   6   7   8   9  10  11               │   │
│  │  Select Track  │  Show Activity  │  Rec LED (slot 11)         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  GREEN BUTTONS (CC 36-47) + Page/Function LEDs                │   │
│  │                                                                │   │
│  │  PAGES (CC 36-43):                                            │   │
│  │  [🟢][🟢][🟢][🟢][🟢][🟢][🟢][🟢]                           │   │
│  │   P1  P2  P3  P4  P5  P6  P7  P8                             │   │
│  │                                                                │   │
│  │  FUNCTIONS (CC 44-47):                                        │   │
│  │  [🟢][🟢][🟢][🟢]                                             │   │
│  │  SEL LOCK PRV SHFT                                            │   │
│  │   44  45  46  47                                              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📋 Complete CC Mapping

### Controls (Track-Specific)
| CC Range | Control | Function | Ableton Mapping |
|----------|---------|----------|-----------------|
| **0-11** | Top Pots | Parameter control | First Rack → Macro 2 |
| **12-23** | Bottom Pots | Parameter control | First Rack → Macro 3 |
| **48-59** | Faders | Parameter control | First Rack → Macro 1 |
| **60** | Encoder | Track scroll | Navigate through tracks |

### Buttons & LEDs
| CC | Color | Button | Function | LED Behavior |
|----|-------|--------|----------|--------------|
| **24-35** | Red | Track buttons | Select track | ON = Activity detected |
| **36-43** | Green | Page 1-8 | Switch page | ON = Current page, BLINK = Locked |
| **44** | Green | SELECT | Hold + Red = Select track | - |
| **45** | Green | LOCK | Hold + Red = Lock/unlock track<br>Double-tap = Toggle LOCKS mode | ON in LOCKS mode |
| **46** | Green | PREVIEW | Hold to preview changes | BLINK when active |
| **47** | Green | SHIFT | Modifier for alternate functions | - |

### Function Combinations
| Combination | Action |
|-------------|--------|
| **SHIFT + CC 44** | *(Reserved for future)* |
| **SHIFT + CC 45 (double-tap)** | Start/stop recording (overdub + automation ARM) |
| **SHIFT + CC 46** | Re-enable all overridden automations |

---

## 📦 Installation

### Prerequisites
- **Ableton Live 11 or 12** (Suite, Standard, or Intro)
- **Faderfox MX12** MIDI controller
- **Max for Live** (included with Suite, optional add-on for Standard/Intro)

### Step 1: Install Remote Script

#### macOS
```bash
# Copy the RemoteScript folder
cp -r RemoteScript/src ~/Library/Preferences/Ableton/Live\ X.X.X/User\ Remote\ Scripts/FaderfoxMX12byYVMA

# Or via iCloud (if syncing preferences)
cp -r RemoteScript/src ~/Library/Mobile\ Documents/com~apple~CloudDocs/Music/Ableton/My\ Ableton\ Presets/User\ Library/Remote\ Scripts/FaderfoxMX12byYVMA
```

#### Windows
```batch
# Copy the RemoteScript folder
xcopy /E /I RemoteScript\src %USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\FaderfoxMX12byYVMA
```

#### Linux
```bash
cp -r RemoteScript/src ~/.local/share/Ableton/Live/User\ Remote\ Scripts/FaderfoxMX12byYVMA
```

### Step 2: Configure MIDI in Ableton

1. Open **Ableton Live Preferences** → **Link, Tempo & MIDI**
2. In **MIDI Ports**:
   - Find your **Faderfox MX12** input
   - Set **Control Surface**: `FaderfoxMX12byYVMA`
   - Set **Input**: `Faderfox MX12`
   - Set **Output**: `Faderfox MX12`
3. **Track** and **Remote** should be OFF for this port
4. Restart Ableton Live

### Step 3: Install M4L Device (Optional, for MIDI tracks)

1. Copy `M4L/MX12byYVMA.amxd` to your User Library:
   - **macOS**: `~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/`
   - **Windows**: `%USERPROFILE%\Documents\Ableton\User Library\Presets\Audio Effects\Max Audio Effect\`
2. In Ableton, drag the device onto **MIDI tracks** you want to control
3. The device monitors MIDI activity and exposes a `midi_active` parameter

**Note**: Audio tracks with `%` suffix work automatically via VU meters (no M4L device needed)

---

## 🚀 Quick Start Guide

### 1. Organize Your Tracks

Add suffixes to track names to organize them into pages:

```
Bass%1          → Page 1 (Button 1)
Drums%1         → Page 1
Lead%2          → Page 2 (Button 2)
Pads%2          → Page 2
FX%             → Filler track (fills empty slots)
Utility%        → Filler track
```

**Smart Filling Rules**:
- `%1` to `%8` = Dedicated pages (priority)
- `%` or `%0` = Filler tracks (auto-distributed)
- Pages with < 12 tracks are filled with `%` tracks
- Pages with ≥ 12 tracks are scrollable (no filling)

### 2. Create Racks

On each track, add a **Rack device** (any type):
- **Instrument Rack**
- **Audio Effect Rack**
- **MIDI Effect Rack**
- **Drum Rack**

The script automatically maps the **first 3 macros**:
- Macro 1 → Fader
- Macro 2 → Top Pot
- Macro 3 → Bottom Pot

### 3. Navigate

- **Press Green Buttons (1-8)**: Switch between pages
- **Turn Encoder (CC 60)**: Scroll within page (if > 12 tracks)
- **Red Buttons**: Select tracks in Ableton

---

## 🔥 Advanced Features

### Virtual Page (LOCKS Mode)

Create a custom collection of tracks from any page:

1. **Hold LOCK (CC 45)** + Press **Red Button** → Add/remove track from virtual page
2. **Double-tap LOCK (CC 45)** → Toggle between PAGE and LOCKS view
3. In LOCKS mode:
   - View only locked tracks
   - CC 45 LED is ON (mode indicator)
   - Scroll with encoder if > 12 locked tracks

**Use case**: Keep bass, drums, and vocals accessible regardless of current page.

### Scroll Position Indicator

When scrolling with the encoder, LEDs show position for 2 seconds:

```
[🟢🟢🟢⚫⚫⚫][⚫⚫⚫⚫⚫⚫]
  LEFT      RIGHT

Left LEDs (0-5) = Tracks hidden on the left (before view)
Right LEDs (6-11) = Tracks hidden on the right (after view)
1 LED = 1 hidden track (max 6 per side)
```

### Preview Mode

Test parameter changes without committing:

1. **Press CC 46 (PREVIEW)** → Backup current state
2. **Hold CC 46** → Modify parameters freely
3. **Release CC 46** → Restore original values

**Use case**: Quickly audition different macro settings.

### Recording Control

- **Single-tap SHIFT + CC 45**: Stop recording + re-enable automations (cleanup)
- **Double-tap SHIFT + CC 45**: Start recording (overdub + automation ARM)
- **Recording LED (slot 11)**: Blinks at 4Hz during recording

### Activity LEDs

- **Audio tracks** with `%` suffix: VU meter monitoring (automatic)
- **MIDI tracks**: Requires M4L device `MX12byYVMA.amxd`
- **Red LEDs (0-10)**: ON when track has activity

---

## 🛠️ Configuration

### Faderfox MX12 Setup

Ensure your MX12 is configured to send:
- **MIDI Channel**: 1 (default)
- **CC Messages**: 0-60 as specified in mapping
- **Encoder Mode**: Absolute (0-127) or Relative

### Track Naming Conventions

| Pattern | Behavior | Example |
|---------|----------|---------|
| `TrackName%1` | Page 1 priority | `Bass%1` |
| `TrackName%2` to `%8` | Pages 2-8 priority | `Drums%2` |
| `TrackName%` | Filler track | `FX%` |
| `TrackName%0` | Same as `%` | `Utility%0` |

### Pickup Mode

Default threshold: **2%** (prevents jumps)

To adjust, edit `RemoteScript/src/config.py`:
```python
PICKUP_THRESHOLD = 0.02  # 2% threshold
```

---

## 📊 Page Organization Examples

### Example 1: Mixed Groups + Fillers
```
Tracks:
- 8 tracks %1 (Drums)
- 15 tracks %2 (Synths)
- 10 tracks % (FX, Utility)

Result:
Page 1: 8 tracks %1 + 4 tracks % = 12 slots filled
Page 2: 15 tracks %2 (scrollable, 3 extra hidden)
Page 3: 6 tracks % + 6 empty = 12 slots
Pages 4-8: Empty
```

### Example 2: Only Filler Tracks
```
Tracks:
- 30 tracks % (all generic)

Result:
Page 1: tracks % 1-12
Page 2: tracks % 13-24
Page 3: tracks % 25-30 + 6 empty
Pages 4-8: Empty
```

### Example 3: Overflowing Groups
```
Tracks:
- 20 tracks %1

Result:
Page 1: 20 tracks %1 (scrollable within page)
- Use encoder to scroll through tracks 1-20
- No filler tracks added
```

---

## 🐛 Troubleshooting

### Script Not Appearing

1. Check folder name: Must be **exactly** `FaderfoxMX12byYVMA`
2. Check folder contents: `__init__.py`, `FaderfoxMX12byYVMA.py`, `config.py`
3. Restart Ableton Live completely
4. Check Log.txt: `~/Library/Preferences/Ableton/Live X.X.X/Log.txt` (macOS)

### LEDs Not Updating

1. Verify **Output** is set to `Faderfox MX12` in MIDI preferences
2. Check MIDI channel (should be 1)
3. Reload script: **Cmd/Ctrl + O** → **Enter**

### Controls Not Responding

1. Verify **Input** is set to `Faderfox MX12`
2. Ensure **Track** and **Remote** are OFF for this MIDI port
3. Check that tracks have rack devices with macros

### Activity LEDs Not Working

- **Audio tracks**: Add `%` suffix to track name
- **MIDI tracks**: Drop `MX12byYVMA.amxd` device on track
- Check Log.txt for listener errors

### Encoder Not Scrolling

1. Ensure page has > 12 tracks
2. Check encoder sends CC 60
3. Try both directions (clockwise/counter-clockwise)
4. Verify encoder mode: Absolute (0-127) or Relative supported

---

## 🎨 LED States Reference

### Green LEDs (Pages/Functions)

| State | Meaning |
|-------|---------|
| **SOLID ON** | Current page |
| **SLOW BLINK (1Hz)** | Track in virtual page + current page button |
| **FAST BLINK (2.5Hz)** | Track in virtual page (not on current page) |
| **OFF** | Inactive |

### Red LEDs (Activity)

| State | Meaning |
|-------|---------|
| **ON** | Track has audio/MIDI activity |
| **BLINK (4Hz)** | Recording active (slot 11 only) |
| **OFF** | No activity |

---

## 📝 Version History

### v3.0.0 (Current)
- **Major**: Smart page filling system
- `%0` treated as `%` (equivalent)
- Pages filled with %1-%8 tracks first, then % tracks
- Fallback: If no %x tracks, fill pages with % only

### v2.9.9
- Intuitive scroll indicator (1 LED = 1 hidden track)
- Directional display (left/right)

### v2.9.8
- Fixed LED persistence in scroll indicator and LOCKS mode

### v2.9.7
- Fixed LED persistence when switching display modes
- Added visual scroll position indicator

### v2.9.6
- Support for absolute encoder mode (0-127)

### v2.9.5
- Differentiated LED blink patterns (fast/slow)

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

---

## 📜 License

This project is licensed under the **Creative Commons Attribution 4.0 International License (CC BY 4.0)**.

You are free to:
- **Share**: Copy and redistribute the material
- **Adapt**: Remix, transform, and build upon the material

Under the following terms:
- **Attribution**: You must give appropriate credit

See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- **Script Development**: Yves-Marie LAINÉ
- **Ableton Live API**: Ableton AG
- **Faderfox MX12**: Faderfox

---

## 📧 Support

For bugs, feature requests, or questions:
- Open an issue on GitHub
- Check existing issues first
- Provide Ableton Live version and Log.txt excerpt

---

**Happy controlling! 🎛️**
