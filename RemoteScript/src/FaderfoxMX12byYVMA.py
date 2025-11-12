"""
Faderfox MX12 Custom Control Surface - LISTENER VERSION
---------------------------------------------------------------------------
Activity detection priority:
1. Audio tracks with '|' → VU meter listener (output_meter_level)
2. MIDI tracks → M4L device parameter listener (midi_active)
3. Fallback → VU meter for MIDI tracks without M4L (instruments with audio output)

⚠️ Note: Les listeners sur paramètres peuvent polluer l'undo history
"""

from __future__ import absolute_import, print_function, unicode_literals
import re
import time
import Live
from _Framework.ControlSurface import ControlSurface
from . import config

VERSION = "3.0.0"  # Major: Smart page filling - |0=|  + |1-|8 priority + | tracks as filler


class FaderfoxMX12byYVMA(ControlSurface):
    """Listener-based Control Surface for Faderfox MX12"""

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self.log_message(f"Faderfox MX12 v{VERSION} - Initializing...")

        # Configuration
        self.DEVICE_NAME = "MX12byYVMA"
        self.NUM_TRACKS = 12
        self.NUM_PAGES = 8
        self.NUM_FUNCTIONS = 4

        # Groups and pages (Phase 1)
        self._track_groups = {}  # {group_id: [tracks...]}
        self._all_tracks_padded = []  # Linear list with None for padding
        self._page_start_positions = []  # Start position of each page in _all_tracks_padded
        self._current_page = 0  # Current page for LED display (0-7)
        self._scroll_offset = 0  # Track offset for track-by-track scrolling (Phase 4)
        self._page_scroll_offset = 0  # LOCAL scroll within current page (respects locks)

        # Legacy (will be removed)
        self._filtered_tracks = []

        # Mappings
        self._mapped_params = {}

        # Virtual page tracks (tracks added to virtual page, shown in PINS mode)
        # Changed from dict to list to preserve order and avoid slot index conflicts
        self._pinned_tracks = []  # List of track objects in order of addition

        # Display mode (Phase X - Simplified pins view)
        self._display_mode = 'page'  # 'page' or 'pins'
        self._last_cc45_press_time = 0  # For double-tap detection on CC 45
        self._last_cc44_press_time = 0  # For double-tap detection on CC 44 (recording)

        # Encoder state (for absolute mode 0-127)
        self._last_encoder_value = None  # Track last encoder value to detect direction

        # Scroll position indicator (visual feedback when scrolling)
        self._scroll_indicator_active = False  # True when showing scroll position
        self._scroll_indicator_end_time = 0  # Time when indicator should turn off

        # Function buttons state (Phase 3 - momentary mode)
        # Note: _select_mode removed - track selection is now the default behavior for red buttons
        self._pin_mode = False    # CC 45 - PIN combo mode (hold)
        self._snapshot_mode = False  # CC 46 - SNAPSHOT toggle mode (active/inactive)
        self._shift_mode = False   # CC 47 - SHIFT modifier (hold for alternate functions)
        self._recording_mode = False  # CC 44 - Recording toggle mode (arrangement + automation)

        # Snapshots (Phase 6) - Toggle mode
        self._snapshot_backup = {}  # Snapshot backup, active while _snapshot_mode = True

        # LEDs
        self._led_states = [0] * 12  # Red (activity)
        self._page_led_states = [0] * 12  # Green (page/pins)
        self._midi_channel = 0

        # Blink counters for green LEDs (pins visualization)
        # Fast: 2.5Hz (75% ON, 25% OFF) pour pinned seul - attire attention
        # Slow: 1Hz (90% ON, 10% OFF) pour page + pinned - moins dérangeant
        self._blink_fast_counter = 0  # 2.5Hz for pinned slots (not on current page)
        self._blink_fast_state = True  # True = ON (75%), False = OFF (25%)
        self._blink_slow_counter = 0  # 1Hz for page + pinned (double function)
        self._blink_slow_state = True  # True = ON (90%), False = OFF (10%)

        # Recording LED blink (red, slot 11) - 4Hz rapid blink
        self._recording_blink_counter = 0  # 4Hz for recording indicator
        self._recording_blink_state = True  # True = ON, False = OFF
        self._recording_led_slot = 11  # Use slot 11 (CC 35 red, CC 47 green) for indicators

        # Snapshot LED blink (green, slot 11) - same 4Hz rapid blink
        self._snapshot_blink_counter = 0  # 4Hz for snapshot indicator
        self._snapshot_blink_state = True  # True = ON, False = OFF

        # Pickup mode tracking
        self.PICKUP_THRESHOLD = 0.02  # 2% tolerance for pickup
        self._control_values = {}  # (track_idx, control_type) -> normalized value (0.0-1.0)
        self._control_midi_values = {}  # (track_idx, control_type) -> MIDI value (0-127) for snapshots

        # Listeners tracking
        self._active_listeners = {}  # (track_idx, listener_type) -> (listener_function, track_object)
        self._param_listeners = {}  # (track_idx, control_type) -> listener_function
        self._suspended_listeners = {}  # Temporary storage for suspended param listeners during bulk operations

        # CPU Optimization: Throttle LED resync to prevent spam
        self._last_resync_time = 0
        self._resync_cooldown = 0.05  # 50ms cooldown between resyncs

        # CPU Optimization: Skip update_display if blink states unchanged
        self._prev_blink_fast_state = True
        self._prev_blink_slow_state = True

        # Setup
        self._scan_tracks()
        self._setup_listeners()

        # Initialize ALL LEDs to known state (FORCE send, ignore state tracking)
        self.log_message("Initializing LEDs...")

        # Activity LEDs (red, CC 24-35) - all OFF
        for i in range(12):
            self._send_midi((0xB0 | self._midi_channel, 24 + i, 0))
            self._led_states[i] = 0

        # Page LEDs (green, CC 36-47) - all OFF except current page
        # Hardware now correctly responds: 127=ON, 0=OFF
        for i in range(12):
            value = 127 if i == self._current_page else 0
            self._send_midi((0xB0 | self._midi_channel, 36 + i, value))
            self._page_led_states[i] = value
            self.log_message(f"Init: CC {36+i} = {value} (page {i}, current={self._current_page})")

        self.log_message(f"Faderfox MX12 v{VERSION} - Ready! Found {len(self._filtered_tracks)} tracks")
        self.show_message(f"Faderfox MX12 v{VERSION} - Ready!")

    # === REQUIRED API METHODS ===

    def suggest_input_port(self):
        """Suggest MIDI input port name"""
        return "Faderfox MX12"

    def suggest_output_port(self):
        """Suggest MIDI output port name"""
        return "Faderfox MX12"

    def can_lock_to_devices(self):
        return False

    def connect_script_instances(self, instanciated_scripts):
        pass

    def refresh_state(self):
        pass

    def build_midi_map(self, midi_map_handle):
        """Register MIDI CCs to receive via receive_midi()"""
        script_handle = self._c_instance.handle()

        # Forward all CCs from Faderfox to receive_midi()
        # CC 0-11: Pots top
        # CC 12-23: Pots bottom
        # CC 24-35: Activity buttons (red)
        # CC 36-47: Page buttons (green)
        # CC 48-59: Faders
        # CC 60: Encoder
        for cc_num in range(61):  # 0-60
            Live.MidiMap.forward_midi_cc(script_handle, midi_map_handle, self._midi_channel, cc_num)

        self.log_message("MIDI map built: forwarding CC 0-60 to receive_midi()")

    # === MIDI HANDLING ===

    def receive_midi(self, midi_bytes):
        if len(midi_bytes) < 3:
            return

        status = midi_bytes[0]
        data1 = midi_bytes[1]
        data2 = midi_bytes[2]

        msg_type = status & 0xF0
        channel = status & 0x0F

        # DEBUG: Log ALL incoming MIDI (first 100 messages)
        if not hasattr(self, '_midi_debug_count'):
            self._midi_debug_count = 0
        if self._midi_debug_count < 100:
            self.log_message(f"MIDI RX: status={status:02X} data1={data1} data2={data2} | msg_type={msg_type:02X} channel={channel}")
            self._midi_debug_count += 1

        if channel != self._midi_channel:
            self.log_message(f"MIDI IGNORED: wrong channel (got {channel}, expected {self._midi_channel})")
            return

        if msg_type == 0xB0:  # Control Change
            self.log_message(f"CC received: CC{data1}={data2}")
            self._handle_cc(data1, data2)

    def _handle_cc(self, cc_num, value):
        # Red buttons (CC 24-35) - NEW: select track by default, pin when CC 45 held
        if 24 <= cc_num <= 35:
            slot_idx = cc_num - 24

            if value > 0:  # Press
                self._force_resync_all_leds()

                # Check which function mode is active
                if self._pin_mode:
                    # PIN mode (CC 45 held): pin/unpin slot
                    self._toggle_pin(slot_idx)
                else:
                    # DEFAULT behavior: select track in Ableton
                    self._select_track(slot_idx)
            else:  # Release
                self._force_resync_all_leds()

        # Page buttons (CC 36-43) - 8 pages
        elif 36 <= cc_num <= 43:
            if value > 0:
                # Resync ALL LEDs on press
                self._force_resync_all_leds()

                page_idx = cc_num - 36

                # Special behavior in PINS mode
                if self._display_mode == 'pins':
                    # Exit PINS mode and go to this page
                    self._display_mode = 'page'
                    self._change_page(page_idx)
                    self.show_message("View: PAGE {} (exited pins)".format(page_idx + 1))
                    self.log_message("Exited PINS mode via page button press (CC {})".format(cc_num))
                else:
                    # Normal page change
                    self._change_page(page_idx)
            else:
                # Button released - resync ALL LEDs again
                self._force_resync_all_leds()

        # Function buttons (CC 44-47) - Phase 3 momentary modes
        elif 44 <= cc_num <= 47:
            self._force_resync_all_leds()
            self._handle_function_button(cc_num, value)

        # Faders (CC 48-59)
        elif 48 <= cc_num <= 59:
            self._handle_fader(cc_num - 48, value)

        # Pots top (CC 0-11)
        elif 0 <= cc_num <= 11:
            self._handle_pot_top(cc_num, value)

        # Pots bottom (CC 12-23)
        elif 12 <= cc_num <= 23:
            self._handle_pot_bottom(cc_num - 12, value)

        # Encoder scroll (CC 60)
        elif cc_num == 60:
            self._handle_encoder_scroll(value)

    # === CONTROL HANDLERS ===

    def _handle_function_button(self, cc_num, value):
        """Handle function buttons (CC 44-47) with SHIFT modifier system

        NOTE: Red buttons now SELECT tracks by default (no function button needed)

        Normal mode:
          CC 44 (single): Stop recording + Re-enable automations (cleanup)
          CC 44 (double): Start recording (arrangement overdub + automation ARM + record)
          CC 45: PIN mode (hold + rouge = pin/unpin) OR double-tap for display mode toggle
          CC 46: SNAPSHOT toggle (save/restore all controls)
          CC 47: SHIFT modifier (hold for alternate functions)

        SHIFT mode (hold CC 47):
          CC 47 + CC 44: [AVAILABLE - Not assigned]
          CC 47 + CC 45: [AVAILABLE - Not assigned]
          CC 47 + CC 46: RE-ENABLE AUTOMATIONS
        """
        if cc_num == 44:  # RECORDING with double-tap detection
            if value > 0:  # Only trigger on press
                if self._shift_mode:
                    # SHIFT + CC44: Available for future feature
                    self.show_message("SHIFT+CC44: Not assigned")
                    self.log_message("SHIFT+CC44 pressed - Available for new feature")
                else:
                    # Check for double-tap (< 300ms between presses)
                    now = time.time()
                    time_since_last_press = now - self._last_cc44_press_time

                    if time_since_last_press < 0.3:
                        # DOUBLE-TAP detected → Start recording
                        self.log_message("Double-tap detected on CC44 ({:.3f}s since last press)".format(time_since_last_press))
                        self._start_recording()
                    else:
                        # SINGLE PRESS → Stop recording + re-enable automations
                        self._stop_recording_and_reenable_automations()

                    # Update last press time for next double-tap detection
                    self._last_cc44_press_time = now

        elif cc_num == 45:  # PIN mode + DOUBLE-TAP for display mode toggle
            if value > 0:
                if self._shift_mode:
                    # SHIFT + PIN: Available for future feature
                    self.show_message("SHIFT+CC45: Not assigned")
                    self.log_message("SHIFT+CC45 pressed - Available for new feature")
                else:
                    # Check for double-tap (< 300ms between presses)
                    now = time.time()
                    time_since_last_press = now - self._last_cc45_press_time

                    if time_since_last_press < 0.3:
                        # DOUBLE-TAP detected → Toggle display mode
                        self.log_message("Double-tap detected on CC45 ({:.3f}s since last press)".format(time_since_last_press))
                        self._toggle_display_mode()
                        # Don't activate pin mode on double-tap
                    else:
                        # SINGLE PRESS → Activate pin mode (normal behavior)
                        self._pin_mode = True
                        self.show_message("PIN mode: Press slot to pin/unpin")
                        self.log_message("PIN mode: ON")

                    # Update last press time for next double-tap detection
                    self._last_cc45_press_time = now
            else:
                # Release: disable PIN mode
                self._pin_mode = False
                # Don't show message on release (too verbose)
                self.log_message("PIN mode: OFF")

        elif cc_num == 46:  # SNAPSHOT toggle (or SHIFT+SNAPSHOT = RE-ENABLE AUTOMATION)
            if value > 0:  # Only trigger on press
                if self._shift_mode:
                    # SHIFT + SNAPSHOT: Re-enable automations
                    self.show_message("Re-enabling automations...")
                    self.log_message("SHIFT+SNAPSHOT: Re-enabling automations")
                    self._reenable_all_automations()
                    self._resync_all_params_to_hardware()
                else:
                    # Normal SNAPSHOT toggle
                    self._toggle_snapshot()

        elif cc_num == 47:  # SHIFT modifier
            if value > 0:
                self._shift_mode = True
                self.show_message("SHIFT mode: ON")
                self.log_message("SHIFT mode: ON - Hold for alternate functions")
            else:
                self._shift_mode = False
                self.show_message("SHIFT mode: OFF")
                self.log_message("SHIFT mode: OFF")

    def _select_track(self, slot_idx):
        """Select track in Ableton (red button press)

        Mode-aware selection:
        - PAGE mode: Select from current page tracks
        - PINS mode: Select from virtual page tracks
        """
        track = None

        if self._display_mode == 'pins':
            # PINS MODE: Get track from virtual page
            virtual_tracks = self._build_virtual_track_list()
            start_idx = self._page_scroll_offset
            visible_tracks = virtual_tracks[start_idx:start_idx + self.NUM_TRACKS]

            if slot_idx < len(visible_tracks):
                track = visible_tracks[slot_idx]
        else:
            # PAGE MODE: Get track from current page only
            start_idx = self._scroll_offset + self._page_scroll_offset
            page_tracks = self._all_tracks_padded[start_idx:start_idx + self.NUM_TRACKS]

            if slot_idx < len(page_tracks):
                track = page_tracks[slot_idx]

        if track is not None:
            # Select track in Live
            self.song().view.selected_track = track
            self.show_message("Selected: {}".format(track.name))
            self.log_message("Selected track: {} (slot {})".format(track.name, slot_idx))
        else:
            self.show_message("Slot {} empty".format(slot_idx + 1))
            self.log_message("Cannot select: slot {} is empty".format(slot_idx))

    def _toggle_pin(self, slot_idx):
        """Toggle track in/out of virtual page (add to PINS view)

        Mode-aware behavior:
        - PAGE mode: Add current page track to virtual page list
        - PINS mode: Remove track from virtual page list

        Uses list to preserve order and avoid slot conflicts
        """
        # Get current track in this slot
        track = None

        if self._display_mode == 'pins':
            # In PINS mode, get track from virtual list
            virtual_tracks = self._build_virtual_track_list()
            start_idx = self._page_scroll_offset
            visible_tracks = virtual_tracks[start_idx:start_idx + self.NUM_TRACKS]

            if slot_idx < len(visible_tracks):
                track = visible_tracks[slot_idx]
        else:
            # In PAGE mode, get track from current page
            start_idx = self._scroll_offset + self._page_scroll_offset
            page_tracks = self._all_tracks_padded[start_idx:start_idx + self.NUM_TRACKS]

            if slot_idx < len(page_tracks):
                track = page_tracks[slot_idx]

        if track is None:
            self.show_message("Slot {} empty, cannot toggle".format(slot_idx + 1))
            return

        # Toggle track in/out of virtual page list
        if track in self._pinned_tracks:
            # Remove from virtual page
            self._pinned_tracks.remove(track)
            self.show_message("Unpinned: {}".format(track.name))
            self.log_message("Unpinned: {}".format(track.name))
        else:
            # Add to virtual page
            self._pinned_tracks.append(track)
            self.show_message("Pinned: {}".format(track.name))
            self.log_message("Pinned: {} (total: {})".format(track.name, len(self._pinned_tracks)))

        self._update_activity_listeners()

    def _start_recording(self):
        """Start recording (double-tap CC 44)

        Enables arrangement overdub + automation ARM + starts recording
        LED indicator: Red LED on slot 11 (CC 35) blinks rapidly during recording
        """
        if self._recording_mode:
            self.show_message("Already recording")
            self.log_message("Recording already active, ignoring start request")
            return

        # START RECORDING
        try:
            # 1. Enable MIDI Arrangement Overdub
            if hasattr(self.song(), 'arrangement_overdub'):
                self.song().arrangement_overdub = True
                self.log_message("Enabled: Arrangement Overdub")

            # 2. Enable Automation ARM
            if hasattr(self.song(), 'session_automation_record'):
                self.song().session_automation_record = True
                self.log_message("Enabled: Automation ARM")

            # 3. Start recording
            if hasattr(self.song(), 'record_mode'):
                self.song().record_mode = True
                self.log_message("Enabled: Record Mode")

            # Set flag and show message
            self._recording_mode = True
            self.show_message("RECORDING STARTED")
            self.log_message("Recording mode: ON (Overdub + Automation ARM + Record)")

        except Exception as e:
            self.show_message("ERROR: Could not start recording")
            self.log_message("Recording start ERROR: {}".format(e))
            self._recording_mode = False

    def _stop_recording_and_reenable_automations(self):
        """Stop recording and re-enable automations (single press CC 44)

        This is the "cleanup" action:
        - Stops recording if active
        - Re-enables all automations that were overridden
        - Resyncs hardware with automation values
        """
        # Stop recording if active
        if self._recording_mode:
            try:
                # Stop record mode
                if hasattr(self.song(), 'record_mode'):
                    self.song().record_mode = False
                    self.log_message("Disabled: Record Mode")

                # Set flag
                self._recording_mode = False
                self.log_message("Recording mode: OFF")

                # Turn off recording LED immediately
                cc_num = 24 + self._recording_led_slot
                self._send_midi((0xB0 | self._midi_channel, cc_num, 0))
                self._led_states[self._recording_led_slot] = 0

            except Exception as e:
                self.show_message("ERROR: Could not stop recording")
                self.log_message("Recording stop ERROR: {}".format(e))

        # Always re-enable automations and resync (even if not recording)
        self.show_message("Re-enabling automations...")
        self.log_message("CC44 cleanup: Re-enabling automations + resyncing hardware")
        self._reenable_all_automations()
        self._resync_all_params_to_hardware()

    def _toggle_snapshot(self):
        """Toggle snapshot mode (CC 46)

        First press: Backup all controls, enter snapshot mode
        Second press: Restore backup, exit snapshot mode

        LED indicator: Green LED on slot 11 (CC 47) blinks rapidly during snapshot
        """
        if not self._snapshot_mode:
            # ACTIVATE SNAPSHOT - backup current state
            self._backup_current_state()
            self._snapshot_mode = True
            self.show_message("SNAPSHOT: Active (controls backed up)")
            self.log_message("Snapshot mode: ON - Controls backed up, will restore on toggle")
        else:
            # DEACTIVATE SNAPSHOT - restore backup
            self._restore_backup()
            self._snapshot_mode = False
            self.show_message("SNAPSHOT: Restored")
            self.log_message("Snapshot mode: OFF - Backup restored")

            # Turn off snapshot LED immediately
            cc_num = 36 + self._recording_led_slot  # Green LED = CC 47
            self._send_midi((0xB0 | self._midi_channel, cc_num, 0))
            self._page_led_states[self._recording_led_slot] = 0

    def _toggle_display_mode(self):
        """Toggle between PAGE and PINS display mode (double-tap CC 45)

        PAGE mode:
        - Shows tracks from current page (normal behavior)
        - Pinned tracks visible if on their original page
        - Green LEDs: page indicator + blink on pinned slots

        PINS mode:
        - Shows ONLY pinned tracks
        - All page buttons (CC 36-43) OFF
        - Green LED CC 45 (slot 9) FIXED ON to indicate PINS mode
        - Encoder scrolls through pinned tracks if > 12
        """
        # CRITICAL: Invalidate LED cache to force resend
        # Use values opposite to what we want to ensure MIDI is sent
        self._page_led_states = [127] * 12  # Invalidate with opposite values

        if self._display_mode == 'page':
            # Switch to PINS mode
            self._display_mode = 'pins'
            num_pins = len(self._pinned_tracks)
            self.show_message("View: PINS ({} pinned tracks)".format(num_pins))
            self.log_message("Display mode: PINS ({} tracks)".format(num_pins))
        else:
            # Switch to PAGE mode
            self._display_mode = 'page'
            self.show_message("View: PAGE (normal)")
            self.log_message("Display mode: PAGE")

        # Reset scroll offset when switching modes
        self._page_scroll_offset = 0

        # Force LED resync and remap
        # Bypass throttle by resetting last resync time
        self._last_resync_time = 0
        self._force_resync_all_leds()
        self._map_current_page()

        # CRITICAL: Update green LEDs immediately after mode switch
        # Without this, LEDs won't update until next blink state change
        self._update_green_leds_with_pins(self._blink_fast_state, self._blink_slow_state)

    def _backup_current_state(self):
        """Backup current control positions (toggle snapshot mode)"""
        self._snapshot_backup = {}

        # Copy all current control MIDI values
        for key, midi_value in self._control_midi_values.items():
            self._snapshot_backup[key] = midi_value

        num_controls = len(self._snapshot_backup)
        self.log_message("Snapshot backup: {} controls backed up".format(num_controls))

    def _restore_backup(self):
        """Restore backup values (toggle snapshot mode) - NO automation re-enable"""
        if not self._snapshot_backup:
            self.log_message("No backup to restore")
            return

        # Suspend param listeners to prevent callback flood (if enabled in config)
        if config.SUSPEND_LISTENERS_DURING_RESTORE:
            self._suspend_param_listeners()

        # Restore all backup values
        for (track_idx, control_type), midi_value in self._snapshot_backup.items():
            # Determine CC number based on control type
            if control_type == 'fader':
                cc_num = 48 + track_idx
            elif control_type == 'pot_top':
                cc_num = 0 + track_idx
            elif control_type == 'pot_bottom':
                cc_num = 12 + track_idx
            else:
                continue

            # Send MIDI to hardware
            self._send_midi((0xB0 | self._midi_channel, cc_num, midi_value))

            # Update parameter if mapped
            param = self._mapped_params.get((track_idx, control_type))
            if param:
                # Normalize and set parameter
                normalized = midi_value / 127.0
                param_range = param.max - param.min
                if param_range > 0:
                    param.value = param.min + param_range * normalized

            # Update internal tracking
            self._control_midi_values[(track_idx, control_type)] = midi_value
            self._control_values[(track_idx, control_type)] = midi_value / 127.0

        num_controls = len(self._snapshot_backup)
        self.log_message("Snapshot restored: {} controls".format(num_controls))

        # Resume param listeners (if they were suspended)
        if config.SUSPEND_LISTENERS_DURING_RESTORE:
            self._resume_param_listeners()

    def _reenable_all_automations(self):
        """Re-enable automation for parameters that have automation

        Only calls re_enable_automation() on parameters that actually have
        automation (automation_state != none). This is like clicking the
        "re-enable automation" arrow button in Live's interface.
        """
        count = 0
        for (track_idx, control_type), param in self._mapped_params.items():
            try:
                # Check if parameter has automation before calling re_enable_automation()
                if not param or not hasattr(param, 'automation_state'):
                    continue

                # Get automation state (Live.DeviceParameter.AutomationState enum)
                # Values: none (0), playing (1), overridden (2)
                automation_state = param.automation_state

                # Only re-enable if parameter has automation (not none)
                if automation_state != Live.DeviceParameter.AutomationState.none:
                    if hasattr(param, 're_enable_automation'):
                        param.re_enable_automation()
                        count += 1
                        self.log_message("  Re-enabled automation: slot {} {} (state was {})".format(
                            track_idx, control_type, automation_state
                        ))
            except Exception as e:
                self.log_message("  ERROR re-enabling slot {} {}: {}".format(
                    track_idx, control_type, e
                ))

        if count > 0:
            self.show_message("Re-enabled {} automations".format(count))
            self.log_message("Automation re-enable complete: {} parameters with automation".format(count))
        else:
            self.show_message("No automations to re-enable")
            self.log_message("No parameters with automation found")

    def _resync_all_params_to_hardware(self):
        """Resync all mapped parameter values to hardware + update trackers

        Called after re-enabling automations to ensure hardware reflects
        the current automation values (not old backup values).

        This prevents value jumps when touching controls after automation
        has resumed control.
        """
        # Suspend param listeners to prevent callback flood (if enabled in config)
        if config.SUSPEND_LISTENERS_DURING_RESYNC:
            self._suspend_param_listeners()

        count = 0
        for (track_idx, control_type), param in self._mapped_params.items():
            try:
                # Determine CC number based on control type
                if control_type == 'fader':
                    cc_num = 48 + track_idx
                elif control_type == 'pot_top':
                    cc_num = 0 + track_idx
                elif control_type == 'pot_bottom':
                    cc_num = 12 + track_idx
                else:
                    continue

                # Read current parameter value from Live
                param_range = param.max - param.min
                if param_range > 0:
                    normalized = (param.value - param.min) / param_range
                else:
                    normalized = 0.0

                # Convert to MIDI value (0-127)
                midi_value = int(normalized * 127)
                midi_value = max(0, min(127, midi_value))  # Clamp

                # Send to hardware
                self._send_midi((0xB0 | self._midi_channel, cc_num, midi_value))

                # Update internal trackers (critical for pickup mode)
                self._control_midi_values[(track_idx, control_type)] = midi_value
                self._control_values[(track_idx, control_type)] = normalized

                count += 1
                self.log_message("  Resynced slot {} {}: value={} (MIDI {})".format(
                    track_idx, control_type, param.value, midi_value
                ))
            except Exception as e:
                self.log_message("  ERROR resyncing slot {} {}: {}".format(
                    track_idx, control_type, e
                ))

        self.log_message("Hardware resync complete: {} parameters".format(count))

        # Resume param listeners (if they were suspended)
        if config.SUSPEND_LISTENERS_DURING_RESYNC:
            self._resume_param_listeners()

    def _handle_encoder_scroll(self, value):
        """Encoder scrolls through virtual track list (mode-aware)

        Supports ABSOLUTE encoder mode (0-127):
        - Detects direction by comparing current value with previous value
        - Incrementing values (5→6→7) = scroll forward
        - Decrementing values (7→6→5) = scroll backward
        - Handles wrap-around (127→0 or 0→127)

        PINS mode:
        - Scrolls through pinned tracks if > 12 pins
        - Shows "PINS: Scroll +X/Y"

        PAGE mode:
        - Scrolls within current page (respects pins)
        - Shows "PAGE: Scroll +X/Y"
        """
        # Detect scroll direction using absolute encoder values (0-127)
        if self._last_encoder_value is None:
            # First call - just store the value, don't scroll
            self._last_encoder_value = value
            return

        # Calculate difference
        diff = value - self._last_encoder_value

        # Detect wrap-around (127→0 or 0→127)
        # If difference is very large, it's a wrap
        if abs(diff) > 64:
            # Wrap detected - reverse the direction
            if diff > 0:
                # 0→127 is actually backward
                scroll_direction = -1
            else:
                # 127→0 is actually forward
                scroll_direction = 1
        elif diff > 0:
            # Normal increment - scroll forward
            scroll_direction = 1
        elif diff < 0:
            # Normal decrement - scroll backward
            scroll_direction = -1
        else:
            # No change
            scroll_direction = 0

        # Store current value for next call
        self._last_encoder_value = value

        # If no movement, return early
        if scroll_direction == 0:
            return

        if self._display_mode == 'pins':
            # PINS MODE: Scroll through pinned tracks
            virtual_tracks = self._build_virtual_track_list()
            total_tracks = len(virtual_tracks)

            if total_tracks <= self.NUM_TRACKS:
                # Update encoder value but don't scroll
                return

            # Calculate max scroll
            max_scroll = total_tracks - self.NUM_TRACKS

            # Scroll based on detected direction
            if scroll_direction > 0:  # Forward
                self._page_scroll_offset = min(self._page_scroll_offset + 1, max_scroll)
            else:  # Backward
                self._page_scroll_offset = max(self._page_scroll_offset - 1, 0)

            # Show position
            self.show_message("PINS: Scroll +{}/{}".format(self._page_scroll_offset, max_scroll))
            self.log_message("PINS scroll: offset={}, max={}, total={}".format(
                self._page_scroll_offset, max_scroll, total_tracks
            ))

        else:  # 'page' mode
            # PAGE MODE: Scroll within page (no pin consideration)
            if not self._all_tracks_padded:
                return

            # Get tracks in current group (until next None or end of list)
            page_start = self._scroll_offset
            tracks_in_group = 0
            for i in range(page_start, len(self._all_tracks_padded)):
                if self._all_tracks_padded[i] is None:
                    break
                tracks_in_group += 1

            # Calculate max local scroll
            # Can scroll if group has more tracks than NUM_TRACKS (12)
            max_local_scroll = max(0, tracks_in_group - self.NUM_TRACKS)

            if max_local_scroll == 0:
                # Update encoder value but don't scroll
                return

            # Scroll based on detected direction
            if scroll_direction > 0:  # Forward
                self._page_scroll_offset = min(self._page_scroll_offset + 1, max_local_scroll)
            else:  # Backward
                self._page_scroll_offset = max(self._page_scroll_offset - 1, 0)

            # Show position
            self.show_message("PAGE: Scroll +{}/{}".format(self._page_scroll_offset, max_local_scroll))
            self.log_message("PAGE scroll: offset={}, max={}, tracks_in_group={}".format(
                self._page_scroll_offset, max_local_scroll, tracks_in_group
            ))

        # Activate scroll position indicator for 2 seconds
        self._scroll_indicator_active = True
        self._scroll_indicator_end_time = time.time() + 2.0

        # Remap with new scroll offset
        self._update_green_leds_with_pins(self._blink_fast_state, self._blink_slow_state)
        self._map_current_page()

    def _change_page(self, page_idx):
        """Change to specified page (0-7) - jumps to page start"""
        # Check if page index is valid
        num_pages = len(self._page_start_positions)

        if page_idx >= num_pages or page_idx < 0:
            self.log_message("Page {} IGNORED (out of range 0-{})".format(
                page_idx, num_pages - 1
            ))
            return

        # Skip if already on this page
        if page_idx == self._current_page:
            self.log_message("Already on page {}, skipping".format(page_idx))
            return

        self.log_message("Changing to page {} (was {})".format(page_idx, self._current_page))
        self._current_page = page_idx
        # Use actual page start position from _page_start_positions
        self._scroll_offset = self._page_start_positions[page_idx]
        # Reset local scroll when changing page
        self._page_scroll_offset = 0

        self.show_message("Page {}/{}".format(page_idx + 1, num_pages))
        # Update green LEDs immediately (update_display will continue updating for blinks)
        self._update_green_leds_with_pins(self._blink_fast_state, self._blink_slow_state)
        self._map_current_page()

    def _handle_fader(self, track_idx, value):
        self._handle_control(track_idx, 'fader', value)

    def _handle_pot_top(self, track_idx, value):
        self._handle_control(track_idx, 'pot_top', value)

    def _handle_pot_bottom(self, track_idx, value):
        self._handle_control(track_idx, 'pot_bottom', value)

    def _handle_control(self, track_idx, control_type, midi_value):
        """Handle control with pickup mode to prevent value jumps"""
        param = self._mapped_params.get((track_idx, control_type))
        if not param:
            return

        # Store MIDI value for snapshots (Phase 6)
        key = (track_idx, control_type)
        self._control_midi_values[key] = midi_value

        # Normalize incoming MIDI value (0-127 → 0.0-1.0)
        incoming_normalized = midi_value / 127.0

        # Get current parameter value (normalized to 0.0-1.0)
        param_range = param.max - param.min
        if param_range > 0:
            param_normalized = (param.value - param.min) / param_range
        else:
            param_normalized = 0.0

        # Check if we've "picked up" the parameter value yet
        if key not in self._control_values:
            # First touch after page change - wait for pickup
            distance = abs(incoming_normalized - param_normalized)
            if distance > self.PICKUP_THRESHOLD:
                # Not close enough - wait for pickup
                self._control_values[key] = incoming_normalized
                return
            else:
                # Close enough - pickup achieved!
                self._control_values[key] = incoming_normalized

        # Update control value tracker
        self._control_values[key] = incoming_normalized

        # Set parameter value
        param.value = param.min + param_range * incoming_normalized

    # === TRACK SCANNING & MAPPING ===

    def _parse_track_group(self, track_name):
        """Parse track name to extract group ID.

        Returns:
            None: Track not in MX12 system
            0: Track with '|' or '|0' (default/fill group)
            1-8: Track with '|1' to '|8'
        """
        if track_name.endswith('|'):
            return 0

        match = re.search(r'\|(\d+)$', track_name)
        if match:
            group_num = int(match.group(1))
            # |0 is treated as | (group 0)
            if group_num == 0:
                return 0
            return group_num if 1 <= group_num <= 8 else None

        return None

    def _scan_tracks(self):
        """Scan tracks and organize into groups with smart page filling

        New logic:
        1. |0 = | (equivalent)
        2. Pages 0-7 filled with |1-|8 tracks first (priority)
        3. If page has < 12 tracks, fill with | tracks (in order)
        4. If page has >= 12 tracks, no filling (scroll within page)
        5. If no |x tracks, fill pages with | tracks only
        """
        # Reset structures
        self._track_groups = {}
        self._all_tracks_padded = []
        self._page_start_positions = []
        self._filtered_tracks = []  # Legacy, keep for compatibility

        # Parse all tracks and organize by group
        for track in self.song().tracks:
            group_id = self._parse_track_group(track.name)

            # Also check M4L device (legacy support)
            if group_id is None and self._find_m4l_device(track) is not None:
                group_id = 0  # Default to group 0

            if group_id is not None:
                if group_id not in self._track_groups:
                    self._track_groups[group_id] = []
                self._track_groups[group_id].append(track)
                self._filtered_tracks.append(track)  # Legacy

        # Get group 0 tracks (| and |0) for filling
        fill_tracks = self._track_groups.get(0, [])
        fill_index = 0  # Track position in fill_tracks list

        # Build pages 0-7 with smart filling
        total_tracks = 0
        has_numbered_groups = any(gid >= 1 for gid in self._track_groups.keys())

        if has_numbered_groups:
            # Mode 1: |1-|8 groups exist → fill each page with |x first, then | tracks
            for page_num in range(8):
                # Record start position of this page
                page_start_pos = len(self._all_tracks_padded)
                self._page_start_positions.append(page_start_pos)

                page_group_id = page_num + 1  # Page 0 = group |1, Page 1 = group |2, etc.
                page_tracks = self._track_groups.get(page_group_id, [])

                # Add |x tracks first
                self._all_tracks_padded.extend(page_tracks)
                total_tracks += len(page_tracks)

                # Fill remaining slots (up to 12) with | tracks if available
                if len(page_tracks) < 12:
                    slots_needed = 12 - len(page_tracks)
                    slots_filled = 0

                    while slots_filled < slots_needed and fill_index < len(fill_tracks):
                        self._all_tracks_padded.append(fill_tracks[fill_index])
                        fill_index += 1
                        slots_filled += 1
                        total_tracks += 1

                    # Pad remaining slots with None if no more | tracks
                    if slots_filled < slots_needed:
                        padding_needed = slots_needed - slots_filled
                        self._all_tracks_padded.extend([None] * padding_needed)

                    self.log_message(
                        "Page {}: {} |{} tracks + {} | tracks (filled to 12)".format(
                            page_num, len(page_tracks), page_group_id, slots_filled
                        )
                    )
                else:
                    # Page has >= 12 tracks, pad to page boundary
                    remainder = len(page_tracks) % 12
                    if remainder != 0:
                        padding_needed = 12 - remainder
                        self._all_tracks_padded.extend([None] * padding_needed)
                        self.log_message(
                            "Page {}: {} |{} tracks (scrollable, padded with {})".format(
                                page_num, len(page_tracks), page_group_id, padding_needed
                            )
                        )
                    else:
                        self.log_message(
                            "Page {}: {} |{} tracks (scrollable)".format(
                                page_num, len(page_tracks), page_group_id
                            )
                        )

        else:
            # Mode 2: No |x groups → fill pages with | tracks only (12 per page)
            page_num = 0
            while fill_index < len(fill_tracks) and page_num < 8:
                # Record start position of this page
                page_start_pos = len(self._all_tracks_padded)
                self._page_start_positions.append(page_start_pos)

                page_tracks_slice = fill_tracks[fill_index:fill_index + 12]
                self._all_tracks_padded.extend(page_tracks_slice)
                total_tracks += len(page_tracks_slice)

                # Pad to 12 if last page has < 12 tracks
                if len(page_tracks_slice) < 12:
                    padding_needed = 12 - len(page_tracks_slice)
                    self._all_tracks_padded.extend([None] * padding_needed)

                self.log_message(
                    "Page {}: {} | tracks (filled from | pool)".format(
                        page_num, len(page_tracks_slice)
                    )
                )

                fill_index += len(page_tracks_slice)
                page_num += 1

        num_pages = len(self._page_start_positions)
        self.log_message(
            "Scan complete: {} tracks, {} groups, {} pages".format(
                total_tracks, len(self._track_groups), num_pages
            )
        )

        # Reset LEDs
        self._led_states = [0] * self.NUM_TRACKS

        # Map first page
        self._map_current_page()

    def _build_virtual_track_list(self):
        """Build virtual track list based on display mode

        Returns:
            List of tracks to display in the 12 slots

        Mode 'pins':
            Returns pinned tracks in order of addition (list preserves order)
            Example: [Bass (added 1st), Drums (added 2nd), Lead (added 3rd), ...]

        Mode 'page':
            Returns tracks from current page (normal behavior)
            Example: [Track1|2, Track2|2, Track3|2, ...]
        """
        if self._display_mode == 'pins':
            # PINS mode: return pinned tracks in order of addition
            # _pinned_tracks is now a list, so just return a copy
            return list(self._pinned_tracks)

        else:  # 'page'
            # PAGE mode: return tracks from current page (normal behavior)
            start_idx = self._scroll_offset + self._page_scroll_offset
            page_tracks = self._all_tracks_padded[start_idx:start_idx + self.NUM_TRACKS]
            # Remove None padding for virtual list
            return [t for t in page_tracks if t is not None]

    def _map_current_page(self):
        """Map tracks from current scroll position to hardware slots

        New behavior with display mode:
        - PAGE mode: Shows ONLY page tracks (no pinned tracks shown)
        - PINS mode: Shows ONLY pinned tracks (virtual page)

        Takes into account:
        - Display mode (_display_mode) for PAGE vs PINS view
        - Global scroll offset (_scroll_offset) for page position (PAGE mode only)
        - Local scroll offset (_page_scroll_offset) for scrolling within virtual list
        - Pinned tracks shown in slot order (PINS mode)
        """
        # Remove old parameter listeners
        self._remove_param_listeners()

        # Clear mappings and pickup state
        self._mapped_params.clear()
        self._control_values.clear()  # Reset pickup mode for all controls

        # Reset all activity LEDs to OFF before remapping
        for i in range(self.NUM_TRACKS):
            self._send_midi((0xB0 | self._midi_channel, 24 + i, 0))
            self._led_states[i] = 0

        if self._display_mode == 'pins':
            # PINS MODE: Show only virtual page tracks (pinned tracks)
            # Build virtual list (pinned tracks sorted by slot index)
            virtual_tracks = self._build_virtual_track_list()

            # Apply scroll offset for navigation if > 12 pins
            start_idx = self._page_scroll_offset
            visible_tracks = virtual_tracks[start_idx:start_idx + self.NUM_TRACKS]

            # Map visible tracks to slots 0-N
            for track_idx in range(min(len(visible_tracks), self.NUM_TRACKS)):
                track = visible_tracks[track_idx]
                if track is not None:
                    self._map_track(track_idx, track)

        else:  # 'page' mode
            # PAGE MODE: Show ONLY page tracks (ignore pinned tracks)
            # Get tracks for current scroll position + local scroll offset
            start_idx = self._scroll_offset + self._page_scroll_offset
            page_tracks = self._all_tracks_padded[start_idx:start_idx + self.NUM_TRACKS]

            # Map page tracks directly (no pin priority)
            for track_idx in range(min(len(page_tracks), self.NUM_TRACKS)):
                track = page_tracks[track_idx]
                if track is not None:
                    self._map_track(track_idx, track)

        # Update listeners for new page (will trigger LED updates)
        self._update_activity_listeners()

    def _map_track(self, track_idx, track):
        rack = self._find_first_rack(track)
        if not rack or len(rack.parameters) < 2:
            return

        macros = rack.parameters[1:]

        # Map and setup bidirectional feedback
        controls = [
            ('fader', 48, 0),    # Fader, CC 48+idx, macro 0
            ('pot_top', 0, 1),   # Pot top, CC 0+idx, macro 1
            ('pot_bottom', 12, 2) # Pot bottom, CC 12+idx, macro 2
        ]

        for control_type, cc_base, macro_idx in controls:
            if macro_idx < len(macros):
                param = macros[macro_idx]
                self._mapped_params[(track_idx, control_type)] = param

                # Add parameter listener for bidirectional feedback
                self._add_param_listener(track_idx, control_type, param, cc_base + track_idx)

                # Send initial value to hardware
                self._send_param_to_hardware(param, cc_base + track_idx)

    def _find_first_rack(self, track):
        """Find first rack device with macros on track

        Supports all rack types:
        - Instrument Rack (InstrumentGroupDevice)
        - Audio Effect Rack (AudioEffectGroupDevice)
        - MIDI Effect Rack (MidiEffectGroupDevice)
        - Drum Rack (DrumGroupDevice)
        """
        for device in track.devices:
            # Generic check: any device with chains and parameters (macros)
            if hasattr(device, 'chains') and hasattr(device, 'parameters'):
                # Check if it has macro parameters (usually index 1+)
                if len(device.parameters) > 1:
                    return device
        return None

    # === PARAMETER FEEDBACK (BIDIRECTIONAL) ===

    def _add_param_listener(self, track_idx, control_type, param, cc_num):
        """Add listener to parameter for bidirectional feedback"""
        # Use closure to capture current values
        def make_listener(idx, ctrl_type, prm, cc):
            return lambda: self._on_param_value_changed(idx, ctrl_type, prm, cc)

        listener = make_listener(track_idx, control_type, param, cc_num)
        if not param.value_has_listener(listener):
            param.add_value_listener(listener)
        self._param_listeners[(track_idx, control_type)] = listener

    def _on_param_value_changed(self, track_idx, control_type, param, cc_num):
        """Called when a mapped parameter changes (e.g., from mouse in Ableton)"""
        self._send_param_to_hardware(param, cc_num)

    def _send_param_to_hardware(self, param, cc_num):
        """Send parameter value to hardware as MIDI CC"""
        try:
            # Normalize parameter value to 0-127
            param_range = param.max - param.min
            if param_range > 0:
                normalized = (param.value - param.min) / param_range
            else:
                normalized = 0.0

            midi_value = int(normalized * 127)
            midi_value = max(0, min(127, midi_value))  # Clamp to 0-127

            self._send_midi((0xB0 | self._midi_channel, cc_num, midi_value))
        except:
            pass

    def _remove_param_listeners(self):
        """Remove all parameter listeners"""
        for key, listener in list(self._param_listeners.items()):
            track_idx, control_type = key
            param = self._mapped_params.get(key)
            if param:
                try:
                    if param.value_has_listener(listener):
                        param.remove_value_listener(listener)
                except:
                    pass
        self._param_listeners.clear()

    def _suspend_param_listeners(self):
        """Temporarily suspend param listeners to prevent callback flood during bulk operations

        Moves listeners from _param_listeners to _suspended_listeners and removes them
        from their parameters. This prevents the flood of callbacks when updating many
        parameters at once (e.g., restore 36 values), which can cause Live to "lose" listeners.
        """
        if not config.ENABLE_PARAM_LISTENERS:
            return  # Listeners disabled, nothing to suspend

        if self._suspended_listeners:
            # Already suspended, don't do it twice
            if config.LOG_LISTENER_SUSPEND_RESUME:
                self.log_message("WARNING: Listeners already suspended, skipping suspend")
            return

        count = 0
        for key, listener in list(self._param_listeners.items()):
            param = self._mapped_params.get(key)
            if param:
                try:
                    if param.value_has_listener(listener):
                        param.remove_value_listener(listener)
                        # Store for resume: (key, listener, param)
                        self._suspended_listeners[key] = (listener, param)
                        count += 1
                except Exception as e:
                    if config.LOG_LISTENER_ADD_REMOVE:
                        self.log_message("ERROR suspending listener {}: {}".format(key, e))

        if config.LOG_LISTENER_SUSPEND_RESUME:
            self.log_message("Suspended {} param listeners".format(count))

    def _resume_param_listeners(self):
        """Resume suspended param listeners after bulk operation completes

        Re-adds listeners that were temporarily suspended to prevent callback flood.
        Called after restore/resync operations finish.
        """
        if not config.ENABLE_PARAM_LISTENERS:
            return  # Listeners disabled, nothing to resume

        if not self._suspended_listeners:
            # Nothing suspended, nothing to resume
            if config.LOG_LISTENER_SUSPEND_RESUME:
                self.log_message("WARNING: No suspended listeners to resume")
            return

        count = 0
        for key, (listener, param) in list(self._suspended_listeners.items()):
            try:
                if not param.value_has_listener(listener):
                    param.add_value_listener(listener)
                    count += 1
            except Exception as e:
                if config.LOG_LISTENER_ADD_REMOVE:
                    self.log_message("ERROR resuming listener {}: {}".format(key, e))

        # Clear suspended storage
        self._suspended_listeners.clear()

        if config.LOG_LISTENER_SUSPEND_RESUME:
            self.log_message("Resumed {} param listeners".format(count))

    # === ACTIVITY DETECTION WITH LISTENERS ===

    def _update_activity_listeners(self):
        """Setup listeners for currently mapped tracks (mode-aware)"""
        # Remove all existing listeners
        self._remove_all_activity_listeners()

        # Get currently mapped tracks based on display mode
        mapped_tracks = []

        if self._display_mode == 'pins':
            # PINS MODE: Get tracks from virtual page
            virtual_tracks = self._build_virtual_track_list()
            start_idx = self._page_scroll_offset
            visible_tracks = virtual_tracks[start_idx:start_idx + self.NUM_TRACKS]

            for track_idx in range(min(len(visible_tracks), self.NUM_TRACKS)):
                track = visible_tracks[track_idx]
                if track is not None:
                    mapped_tracks.append((track_idx, track))

        else:  # 'page' mode
            # PAGE MODE: Get tracks from current page only
            start_idx = self._scroll_offset + self._page_scroll_offset
            page_tracks = self._all_tracks_padded[start_idx:start_idx + self.NUM_TRACKS]

            for track_idx in range(min(len(page_tracks), self.NUM_TRACKS)):
                track = page_tracks[track_idx]
                if track is not None:
                    mapped_tracks.append((track_idx, track))

        # Add listeners for each mapped track
        for track_idx, track in mapped_tracks:
            self._add_activity_listener(track_idx, track)

        self.log_message("Setup {} activity listeners".format(len(mapped_tracks)))

        # Force immediate LED update for current state (don't wait for next change)
        self._force_activity_led_update()

    def _force_activity_led_update(self):
        """Force immediate LED update by reading current activity state (mode-aware)"""
        self.log_message("_force_activity_led_update: mode={}, scroll_offset={}, page_scroll_offset={}".format(
            self._display_mode, self._scroll_offset, self._page_scroll_offset
        ))

        # Get currently mapped tracks based on display mode
        tracks_to_update = []

        if self._display_mode == 'pins':
            # PINS MODE: Get tracks from virtual page
            virtual_tracks = self._build_virtual_track_list()
            start_idx = self._page_scroll_offset
            visible_tracks = virtual_tracks[start_idx:start_idx + self.NUM_TRACKS]

            for track_idx in range(min(len(visible_tracks), self.NUM_TRACKS)):
                track = visible_tracks[track_idx]
                if track is not None:
                    tracks_to_update.append((track_idx, track))

        else:  # 'page' mode
            # PAGE MODE: Get tracks from current page only
            start_idx = self._scroll_offset + self._page_scroll_offset
            page_tracks = self._all_tracks_padded[start_idx:start_idx + self.NUM_TRACKS]

            for track_idx in range(min(len(page_tracks), self.NUM_TRACKS)):
                track = page_tracks[track_idx]
                if track is not None:
                    tracks_to_update.append((track_idx, track))

        # Update LEDs for each mapped track
        for track_idx, track in tracks_to_update:

            # Check activity based on track type
            is_audio = self._is_audio_track(track)

            if is_audio and track.name.endswith('|'):
                # Audio track - read VU meter
                try:
                    level = max(track.output_meter_left, track.output_meter_right)
                    new_value = 127 if level > 0.001 else 0
                    cc_num = 24 + track_idx
                    self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                    self._led_states[track_idx] = new_value
                    self.log_message(f"  Slot {track_idx} ({track.name}): VU={level:.3f} -> LED={new_value}")
                except Exception as e:
                    self.log_message(f"  Slot {track_idx} VU error: {e}")
            else:
                # MIDI track - Try M4L device first, fallback to VU meter
                device = self._find_m4l_device(track)
                if device:
                    # M4L device found
                    for param in device.parameters:
                        if param.name == "midi_active":
                            try:
                                param_value = param.value
                                new_value = 127 if param_value > 0 else 0
                                cc_num = 24 + track_idx
                                self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                                self._led_states[track_idx] = new_value
                                self.log_message(f"  Slot {track_idx} ({track.name}): M4L param={param_value} -> LED={new_value}")
                            except Exception as e:
                                self.log_message(f"  Slot {track_idx} M4L error: {e}")
                            break
                else:
                    # No M4L device → Fallback to VU meter (MIDI with instrument)
                    try:
                        level = max(track.output_meter_left, track.output_meter_right)
                        new_value = 127 if level > 0.001 else 0
                        cc_num = 24 + track_idx
                        self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                        self._led_states[track_idx] = new_value
                        self.log_message(f"  Slot {track_idx} ({track.name}): VU fallback={level:.3f} -> LED={new_value}")
                    except Exception as e:
                        self.log_message(f"  Slot {track_idx} VU fallback error: {e}")

    def _add_activity_listener(self, track_idx, track):
        """Add appropriate listener based on track type

        Priority order:
        1. Audio tracks with '|' → VU meter listener
        2. MIDI tracks → Try M4L device listener
        3. Fallback → VU meter (MIDI tracks with instruments generate audio)
        """
        # First check if it's a real audio track (has VU meters)
        is_audio = self._is_audio_track(track)

        # Audio track with '|' → VU meter listener
        if is_audio and track.name.endswith('|'):
            try:
                # Audio track - listen to output_meter_level
                # Use closure to capture current values (not references)
                def make_vu_listener(idx, trk):
                    return lambda: self._on_vu_meter_change(idx, trk)

                listener = make_vu_listener(track_idx, track)
                if not track.output_meter_level_has_listener(listener):
                    track.add_output_meter_level_listener(listener)
                # Store listener AND track for proper cleanup
                self._active_listeners[(track_idx, 'vu')] = (listener, track)
                self.log_message("Added VU listener for slot {}: {} (Audio)".format(track_idx, track.name))
            except:
                pass
        else:
            # MIDI track or audio without '|' → Try M4L device first
            device = self._find_m4l_device(track)
            if device:
                # M4L device found → Use parameter listener
                for param in device.parameters:
                    if param.name == "midi_active":
                        # Use closure to capture current values (not references)
                        def make_m4l_listener(idx, prm):
                            return lambda: self._on_m4l_param_change(idx, prm)

                        listener = make_m4l_listener(track_idx, param)
                        if not param.value_has_listener(listener):
                            param.add_value_listener(listener)
                        # Store listener AND track for proper cleanup
                        self._active_listeners[(track_idx, 'm4l')] = (listener, track)
                        self.log_message("Added M4L listener for slot {}: {} (M4L)".format(track_idx, track.name))
                        break
            else:
                # No M4L device → Fallback to VU meter
                # (MIDI tracks with instruments generate audio output)
                try:
                    def make_vu_listener(idx, trk):
                        return lambda: self._on_vu_meter_change(idx, trk)

                    listener = make_vu_listener(track_idx, track)
                    if not track.output_meter_level_has_listener(listener):
                        track.add_output_meter_level_listener(listener)
                    self._active_listeners[(track_idx, 'vu')] = (listener, track)
                    self.log_message("Added VU listener (fallback) for slot {}: {} (MIDI with audio output)".format(track_idx, track.name))
                except Exception as e:
                    # VU meter not available (pure MIDI track with no audio)
                    self.log_message("WARNING: No listener for slot {}: {} (no M4L device, no audio output)".format(track_idx, track.name))

    def _is_audio_track(self, track):
        """Check if track is audio (has VU meters) - safe wrapper"""
        try:
            # Try to access output_meter_left - if it works, it's an audio track
            _ = track.output_meter_left
            return True
        except:
            # MIDI tracks throw exception when accessing output_meter_left
            return False

    def _on_vu_meter_change(self, track_idx, track):
        """VU meter listener callback"""
        try:
            level = max(track.output_meter_left, track.output_meter_right)
            new_value = 127 if level > 0.001 else 0

            if self._led_states[track_idx] != new_value:
                cc_num = 24 + track_idx
                self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                self._led_states[track_idx] = new_value
        except:
            pass

    def _on_m4l_param_change(self, track_idx, param):
        """M4L parameter listener callback"""
        try:
            new_value = 127 if param.value > 0 else 0

            # Debug logging for slots 8-11
            if track_idx >= 8:
                self.log_message(f"M4L callback slot {track_idx}: param={param.value}, new_value={new_value}")

            if self._led_states[track_idx] != new_value:
                cc_num = 24 + track_idx
                self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                self._led_states[track_idx] = new_value

                # Debug logging for MIDI send
                if track_idx >= 8:
                    self.log_message(f"Sent MIDI: CC {cc_num} = {new_value}")
        except Exception as e:
            if track_idx >= 8:
                self.log_message(f"ERROR in M4L callback slot {track_idx}: {e}")

    def _remove_all_activity_listeners(self):
        """Remove all activity listeners (using stored track references)"""
        for key, (listener, track) in list(self._active_listeners.items()):
            track_idx, listener_type = key

            try:
                if listener_type == 'vu':
                    if track.output_meter_level_has_listener(listener):
                        track.remove_output_meter_level_listener(listener)
                        self.log_message("Removed VU listener from slot {}".format(track_idx))
                elif listener_type == 'm4l':
                    device = self._find_m4l_device(track)
                    if device:
                        for param in device.parameters:
                            if param.name == "midi_active":
                                if param.value_has_listener(listener):
                                    param.remove_value_listener(listener)
                                    self.log_message("Removed M4L listener from slot {}".format(track_idx))
                                break
            except Exception as e:
                self.log_message("Error removing listener slot {}: {}".format(track_idx, e))

        self._active_listeners.clear()
        self.log_message("All activity listeners cleared")

    def _find_m4l_device(self, track):
        """Find M4L device on track"""
        try:
            for device in track.devices:
                if device.name == self.DEVICE_NAME or self.DEVICE_NAME in device.name:
                    return device
        except:
            pass
        return None

    # === LED UPDATES ===

    def _update_page_leds(self):
        """Update green LEDs (CC 36-47): 8 page buttons + 4 function buttons

        DEPRECATED: This method is kept for backward compatibility but is now
        replaced by _update_green_leds_with_pins() which handles page + pins.
        Only used during initialization.
        """
        updated = []

        # Page buttons (CC 36-43)
        for i in range(8):
            cc_num = 36 + i
            # Normal polarity: 127=ON, 0=OFF
            new_value = 127 if i == self._current_page else 0
            if self._page_led_states[i] != new_value:
                self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                self._page_led_states[i] = new_value
                updated.append("CC{}={}".format(cc_num, new_value))

        # Function buttons (CC 44-47) - OFF for now (Phase 5 will add alternance)
        for i in range(8, 12):
            cc_num = 36 + i  # 44-47
            new_value = 0  # OFF
            if self._page_led_states[i] != new_value:
                self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                self._page_led_states[i] = new_value
                updated.append("CC{}={}".format(cc_num, new_value))

        if updated:
            self.log_message("Page LEDs updated: {}".format(', '.join(updated)))

    def _get_track_origin_page(self, track):
        """Find which page a track originally belongs to (without locks)"""
        for idx, t in enumerate(self._all_tracks_padded):
            if t is not None and id(t) == id(track):
                # Find which page this index belongs to using _page_start_positions
                for page_idx in range(len(self._page_start_positions)):
                    page_start = self._page_start_positions[page_idx]
                    # Last page check
                    if page_idx == len(self._page_start_positions) - 1:
                        if idx >= page_start:
                            return page_idx
                    else:
                        page_end = self._page_start_positions[page_idx + 1]
                        if page_start <= idx < page_end:
                            return page_idx
        return None

    def _force_resync_green_leds(self):
        """Force complete resync of green LEDs (after hardware button press/release)"""
        # Reset state to force resend of all LEDs
        self._page_led_states = [0] * 12  # All OFF
        # Update with current blink states
        self._update_green_leds_with_pins(self._blink_fast_state, self._blink_slow_state)

    def _force_resync_all_leds(self):
        """Force complete resync of ALL LEDs (red activity + green page/pins)

        Called on every button press/release to prevent hardware local toggle
        from "breaking" the display.

        CPU Optimizations:
        - Throttle: 50ms cooldown to prevent spam on rapid button presses
        - Cache-based: Use cached LED states instead of re-reading VU/M4L
        """
        # OPTIMIZATION 1: Throttle - Skip if called too recently
        now = time.time()
        if now - self._last_resync_time < self._resync_cooldown:
            return  # Skip this resync, too soon
        self._last_resync_time = now

        # OPTIMIZATION 2: Cache-based resync
        # Instead of re-reading VU meters and M4L params, use cached LED states
        # that are already kept up-to-date by listeners

        # Store current states before reset
        cached_activity_states = list(self._led_states)  # Copy current activity LED states
        cached_page_states = list(self._page_led_states)  # Copy current page LED states

        # Reset states to force resend (hardware might have toggled locally)
        self._led_states = [127] * 12  # Invalidate cache (activity LEDs)
        self._page_led_states = [0] * 12  # Invalidate cache (page LEDs)

        # Resync activity LEDs (red, CC 24-35) - use CACHED values
        for track_idx in range(self.NUM_TRACKS):
            # Use cached state updated by listeners (no VU/M4L read!)
            cached_value = cached_activity_states[track_idx]
            cc_num = 24 + track_idx
            self._send_midi((0xB0 | self._midi_channel, cc_num, cached_value))
            self._led_states[track_idx] = cached_value

        # Resync page/pin LEDs (green, CC 36-47)
        self._update_green_leds_with_pins(self._blink_fast_state, self._blink_slow_state)

    def _update_scroll_position_indicator(self):
        """Show scroll position indicator on green LEDs for 2 seconds after scrolling

        Depth indicator visualization: Shows how deep you scrolled from start
        - LEDs fill from RIGHT to LEFT (11 → 0) to show scroll depth
        - 1 LED = 1 track scrolled from start position
        - All LEDs OFF = at start position (offset 0)

        Example with 24 tracks in group:
        - Scroll offset 0 (viewing 1-12): All OFF (at start)
        - Scroll offset 1 (viewing 2-13): LED 11 ON (1 track deep)
        - Scroll offset 3 (viewing 4-15): LEDs 9,10,11 ON (3 tracks deep)
        - Scroll offset 12 (viewing 13-24): All 12 LEDs ON (12 tracks deep)

        IMPORTANT: Forces ALL LEDs to update (ignores cache) to ensure clean display
        """
        # Get scroll offset (how deep we are from start)
        if self._display_mode == 'locks':
            offset = self._page_scroll_offset
        else:
            offset = self._page_scroll_offset

        # If at start position, turn all OFF
        if offset == 0:
            for i in range(12):
                cc_num = 36 + i
                self._send_midi((0xB0 | self._midi_channel, cc_num, 0))
                self._page_led_states[i] = 0
            return

        # Calculate how many LEDs to light (max 12)
        num_leds = min(offset, 12)

        # FORCE UPDATE: Set all LEDs
        # Fill from RIGHT to LEFT (LED 11, 10, 9... down to 0)
        for i in range(12):
            cc_num = 36 + i
            new_value = 0  # Default: OFF

            # Light LEDs from right (11) to left (0)
            # Example: offset=3 → LEDs 11, 10, 9 ON
            if i >= (12 - num_leds):
                new_value = 127  # ON

            # FORCE UPDATE: Always send MIDI (ignore cache)
            self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
            self._page_led_states[i] = new_value

    def _update_green_leds_with_pins(self, fast_blink, slow_blink):
        """Update all 12 green LEDs with display mode awareness

        Args:
            fast_blink: 2.5Hz blink for virtual page tracks (not on current page)
            slow_blink: 1Hz blink for double function (virtual page + current page)

        SCROLL INDICATOR MODE (temporary, 2 seconds after scroll):
        - Shows scroll position visualization
        - Green LEDs represent entire track list
        - OFF = visible tracks, ON = hidden tracks

        PINS MODE:
        - CC 36-43 (page buttons): ALL OFF (no page indicator)
        - CC 45 (slot 9): FIXED ON (PINS mode indicator)
        - CC 46-47 (slots 10-11): Snapshot/Recording LEDs (handled in update_display)

        PAGE MODE (differentiated patterns):
        - Track in virtual page + current page button: SLOW BLINK 1Hz (💫 double function)
        - Track in virtual page (not page button): FAST BLINK 2.5Hz (⚡ attention)
        - Current page button (no virtual track): FIXED ON (💡 page indicator)
        - This provides clear visual differentiation for all states
        """
        # Priority 1: Scroll position indicator (overrides everything for 2 seconds)
        if self._scroll_indicator_active:
            self._update_scroll_position_indicator()
            return

        if self._display_mode == 'pins':
            # PINS MODE: All page buttons OFF, CC 45 ON
            # FORCE UPDATE: Always send MIDI (ignore cache) to ensure clean display
            for i in range(12):
                cc_num = 36 + i
                new_value = 0  # Default: OFF

                # CC 45 (slot 9): FIXED ON to indicate PINS mode
                if i == 9:  # Slot 9 = CC 45
                    new_value = 127

                # CC 46-47 (slots 10-11): Snapshot/Recording handled elsewhere
                # Don't override if snapshot or recording is active
                if i == self._recording_led_slot:
                    # Skip - handled by update_display() for snapshot LED
                    continue

                # FORCE UPDATE: Always send MIDI (ignore cache)
                self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                self._page_led_states[i] = new_value

        else:  # 'page' mode
            # PAGE MODE: Page indicator + virtual page membership visualization
            # Get current page tracks to check if they're in virtual page
            start_idx = self._scroll_offset + self._page_scroll_offset
            page_tracks = self._all_tracks_padded[start_idx:start_idx + self.NUM_TRACKS]

            for i in range(12):
                cc_num = 36 + i
                new_value = 0  # Default: OFF (127=ON, 0=OFF)

                # Check if track in this slot is in virtual page
                track_in_virtual_page = False
                if i < len(page_tracks) and page_tracks[i] is not None:
                    track_in_virtual_page = page_tracks[i] in self._pinned_tracks

                # Determine LED pattern based on context
                if track_in_virtual_page:
                    # Track is in virtual page
                    # Check if this is ALSO a page button for current page (double function)
                    if i < 8 and i == self._current_page:
                        # DOUBLE FUNCTION: Track in virtual page + current page button
                        # → SLOW BLINK (1Hz) - subtle, both functions visible
                        new_value = 127 if slow_blink else 0
                    else:
                        # Track in virtual page ONLY (not current page button)
                        # → FAST BLINK (2.5Hz) - attracts attention
                        new_value = 127 if fast_blink else 0

                # Page button - show current page if not in virtual page
                elif i < 8 and i == self._current_page:
                    # Current page, no track in virtual page → FIXED ON
                    new_value = 127

                # CC 46-47 (slots 10-11): Snapshot/Recording handled elsewhere
                # Don't override if snapshot or recording is active
                if i == self._recording_led_slot:
                    # Skip - handled by update_display() for snapshot LED
                    continue

                # Update LED
                if self._page_led_states[i] != new_value:
                    self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                    self._page_led_states[i] = new_value

    # === LISTENERS & DISPLAY ===

    def _setup_listeners(self):
        self.song().add_tracks_listener(self._on_tracks_changed)

    def _on_tracks_changed(self):
        self.log_message("Tracks changed - rescanning")
        self._scan_tracks()

    def update_display(self):
        """Called ~10Hz by Ableton for display updates and blinking

        CPU Optimization: Only update LEDs when blink state actually changes
        - Before: 10 calls/sec to _update_green_leds_with_pins()
        - After: ~7 calls/sec (only on blink transitions: 2.5Hz fast + 1Hz slow)
        - Reduction: 30% less function calls
        """

        # Check if scroll indicator should be deactivated
        if self._scroll_indicator_active and time.time() >= self._scroll_indicator_end_time:
            self._scroll_indicator_active = False
            # Force LED update to restore normal display
            self._update_green_leds_with_pins(self._blink_fast_state, self._blink_slow_state)

        # Fast blink: 2.5Hz = 400ms cycle (3 cycles ON, 1 cycle OFF = 75/25)
        # Pour pinned seul (pas page courante) - rapide pour attirer l'attention
        # Note: update_display() appelé à ~10Hz (100ms), donc 4 compteurs = 400ms cycle
        self._blink_fast_counter += 1
        if self._blink_fast_counter <= 3:
            self._blink_fast_state = True  # ON (75% du temps)
        else:
            self._blink_fast_state = False  # OFF (25% du temps)

        if self._blink_fast_counter >= 4:  # Reset cycle 400ms
            self._blink_fast_counter = 0

        # Slow blink: 1Hz = 1000ms cycle (9 cycles ON, 1 cycle OFF = 90/10)
        # Pour page courante + pinned (double fonction) - moins dérangeant
        # Note: update_display() appelé à ~10Hz (100ms), donc 10 compteurs = 1000ms cycle
        self._blink_slow_counter += 1
        if self._blink_slow_counter <= 9:
            self._blink_slow_state = True  # ON (90% du temps)
        else:
            self._blink_slow_state = False  # OFF (10% du temps)

        if self._blink_slow_counter >= 10:  # Reset cycle 1000ms
            self._blink_slow_counter = 0

        # Recording LED blink: 4Hz = 250ms cycle (fast for attention, 50/50 duty)
        # Red LED on slot 11 (CC 35) blinks rapidly during recording
        # Note: update_display() appelé à ~10Hz (100ms), donc 2.5 compteurs ≈ 250ms cycle
        if self._recording_mode:
            self._recording_blink_counter += 1
            if self._recording_blink_counter <= 1:  # ON for ~100ms (50%)
                self._recording_blink_state = True
            else:
                self._recording_blink_state = False  # OFF for ~100ms (50%)

            if self._recording_blink_counter >= 2:  # Reset cycle ~250ms (4Hz)
                self._recording_blink_counter = 0

            # Update recording LED immediately (don't wait for optimization)
            cc_num = 24 + self._recording_led_slot
            new_value = 127 if self._recording_blink_state else 0
            if self._led_states[self._recording_led_slot] != new_value:
                self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                self._led_states[self._recording_led_slot] = new_value

        # Snapshot LED blink: 4Hz = 250ms cycle (same as recording, 50/50 duty)
        # Green LED on slot 11 (CC 47) blinks rapidly during active snapshot mode
        # Note: update_display() appelé à ~10Hz (100ms), donc 2.5 compteurs ≈ 250ms cycle
        if self._snapshot_mode:
            self._snapshot_blink_counter += 1
            if self._snapshot_blink_counter <= 1:  # ON for ~100ms (50%)
                self._snapshot_blink_state = True
            else:
                self._snapshot_blink_state = False  # OFF for ~100ms (50%)

            if self._snapshot_blink_counter >= 2:  # Reset cycle ~250ms (4Hz)
                self._snapshot_blink_counter = 0

            # Update snapshot LED immediately (don't wait for optimization)
            cc_num = 36 + self._recording_led_slot  # Green LED = CC 47
            new_value = 127 if self._snapshot_blink_state else 0
            if self._page_led_states[self._recording_led_slot] != new_value:
                self._send_midi((0xB0 | self._midi_channel, cc_num, new_value))
                self._page_led_states[self._recording_led_slot] = new_value

        # OPTIMIZATION: Only update LEDs if blink state actually changed
        # This reduces function calls from 100Hz to ~14Hz (fast 10Hz + slow 4Hz)
        blink_changed = (self._blink_fast_state != self._prev_blink_fast_state or
                         self._blink_slow_state != self._prev_blink_slow_state)

        if blink_changed:
            self._update_green_leds_with_pins(self._blink_fast_state, self._blink_slow_state)
            self._prev_blink_fast_state = self._blink_fast_state
            self._prev_blink_slow_state = self._blink_slow_state

    def disconnect(self):
        self.log_message("Disconnecting Faderfox MX12 (LISTENER VERSION)")

        # Remove all listeners
        self._remove_all_activity_listeners()
        self._remove_param_listeners()

        if self.song().tracks_has_listener(self._on_tracks_changed):
            self.song().remove_tracks_listener(self._on_tracks_changed)

        # Turn off all LEDs
        for i in range(12):
            self._send_midi((0xB0 | self._midi_channel, 24 + i, 0))  # Activity LEDs off
            self._send_midi((0xB0 | self._midi_channel, 36 + i, 0))  # Page LEDs off
