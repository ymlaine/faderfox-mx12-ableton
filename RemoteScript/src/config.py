"""
Configuration for Faderfox MX12 Control Surface
---------------------------------------------------------------------------
Adjust these parameters to tune behavior without modifying the main code.
Change values and reload script (Cmd+O → Enter) to test different settings.
"""

# === BASIC SETTINGS ===
TRACK_MARKER = "|"
TRACKS_PER_PAGE = 12
SHOW_MESSAGES = True
LOG_LEVEL = 1

# === PARAMETER LISTENERS (bidirectional feedback) ===
# Master switch for bidirectional feedback (hardware ← Live)
ENABLE_PARAM_LISTENERS = True

# Suspend listeners during bulk parameter updates to avoid callback flood
# This prevents listeners from being triggered during restore/resync operations
# which can cause Live to "lose" listeners due to callback overload
SUSPEND_LISTENERS_DURING_RESTORE = True   # During snapshot restore (CC 46 release)
SUSPEND_LISTENERS_DURING_RESYNC = True    # During automation resync (SHIFT+CC46)

# === ACTIVITY DETECTION ===
# Enable/disable different types of activity listeners
ENABLE_VU_LISTENERS = True       # VU meter listeners for audio tracks
ENABLE_M4L_LISTENERS = True      # M4L device parameter listeners for MIDI tracks
ENABLE_VU_FALLBACK = True        # VU meter fallback for MIDI tracks without M4L

# === DEBUG / LOGGING ===
# Enable detailed logging for troubleshooting (check Ableton Log.txt)
LOG_LISTENER_ADD_REMOVE = True   # Log when param listeners are added/removed
LOG_LISTENER_SUSPEND_RESUME = True  # Log suspend/resume operations
LOG_PARAM_CHANGES = False        # Log every parameter change (VERY verbose!)
LOG_MIDI_SEND = False            # Log every MIDI message sent (VERY verbose!)

# === PERFORMANCE ===
# LED resync throttle (seconds) - prevents spam on rapid button presses
LED_RESYNC_COOLDOWN = 0.05       # 50ms cooldown between LED resyncs

# Pickup mode tolerance (0.0-1.0) - how close hardware must be to parameter value
# Lower = more precise pickup required, Higher = easier to pick up
PICKUP_THRESHOLD = 0.02          # 2% tolerance

# Activity detection threshold for VU meters
ACTIVITY_THRESHOLD = 0.001       # Minimum VU level to trigger activity LED

# === BLINK PATTERNS (LEDs vertes pour locks) ===
# Fast blink for locked slots not on current page (10Hz = 100ms cycle)
BLINK_FAST_ON_CYCLES = 9         # ON for 90ms (90% duty cycle)
BLINK_FAST_OFF_CYCLES = 1        # OFF for 10ms (10% duty cycle)

# Slow blink for locked slots on current page (4Hz = 250ms cycle)
BLINK_SLOW_ON_CYCLES = 22        # ON for 220ms (~88% duty cycle)
BLINK_SLOW_OFF_CYCLES = 3        # OFF for 30ms (~12% duty cycle)
