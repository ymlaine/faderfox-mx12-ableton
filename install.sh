#!/bin/bash
# Faderfox MX12 Control Surface - Installation Script (macOS/Linux)

set -e

echo "🎛️  Faderfox MX12 Control Surface - Installer"
echo "============================================="
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "📍 Detected: macOS"

    # Try iCloud path first (most common for modern Ableton)
    ICLOUD_PATH="$HOME/Library/Mobile Documents/com~apple~CloudDocs/Music/Ableton/My Ableton Presets/User Library/Remote Scripts"
    LOCAL_PATH="$HOME/Library/Preferences/Ableton"

    if [ -d "$ICLOUD_PATH" ]; then
        INSTALL_PATH="$ICLOUD_PATH/FaderfoxMX12byYVMA"
        echo "📂 Installing to: $INSTALL_PATH (iCloud)"
    else
        # Find Ableton version
        ABLETON_VERSIONS=$(ls "$LOCAL_PATH" 2>/dev/null | grep "Live" | sort -r)
        if [ -z "$ABLETON_VERSIONS" ]; then
            echo "❌ Error: No Ableton Live installation found"
            echo "   Please install Ableton Live first"
            exit 1
        fi

        LATEST_VERSION=$(echo "$ABLETON_VERSIONS" | head -1)
        INSTALL_PATH="$LOCAL_PATH/$LATEST_VERSION/User Remote Scripts/FaderfoxMX12byYVMA"
        echo "📂 Installing to: $INSTALL_PATH"
    fi

elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "📍 Detected: Linux"
    INSTALL_PATH="$HOME/.local/share/Ableton/Live/User Remote Scripts/FaderfoxMX12byYVMA"
    echo "📂 Installing to: $INSTALL_PATH"
else
    echo "❌ Error: Unsupported OS"
    echo "   Please use install.bat for Windows"
    exit 1
fi

# Create directory
echo "📁 Creating directory..."
mkdir -p "$INSTALL_PATH"

# Copy files
echo "📦 Copying files..."
cp -r RemoteScript/src/* "$INSTALL_PATH/"

# Verify installation
if [ -f "$INSTALL_PATH/FaderfoxMX12byYVMA.py" ]; then
    echo ""
    echo "✅ Installation complete!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Restart Ableton Live"
    echo "   2. Go to Preferences → Link, Tempo & MIDI"
    echo "   3. Set Control Surface to 'FaderfoxMX12byYVMA'"
    echo "   4. Set Input/Output to 'Faderfox MX12'"
    echo ""
    echo "📖 For detailed setup, see README.md"
else
    echo "❌ Installation failed"
    echo "   Please install manually (see README.md)"
    exit 1
fi
