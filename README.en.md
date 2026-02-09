# vrcsol

VRChat monitoring and Discord Webhook integration GUI application.

## Requirements

- Windows 10 / 11 (64-bit recommended)
- Python 3.14 or later (when running from source)
- python-osc package

The distribution structure consists of the root folder containing README and the Start GUI shortcut, with all source files located in the `source` subfolder.

## How to Run

### Recommended: Start from Shortcut

Double-click the "Start GUI" shortcut in the root folder.

### Command Line

PowerShell:

```powershell
cd .\source
.\start_gui.bat
```

Or from the root:

```powershell
Start-Process -FilePath '.\source\start_gui.bat'
```

### Development: Run from Source

```powershell
cd .\source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install python-osc
python gui.py
```

## Configuration File Paths

- User settings: `%APPDATA%\vrcsol\settings.json`
- Biome messages: `source\biome message.txt`
- Icon images: `source\biome icons\`

## Usage

1. Launch the GUI.
2. Configure Transport (OSC / Discord), Webhook URL, server name, etc.
3. Click "Test Webhook" to verify sending.
4. Click "Start" to begin monitoring, "Stop" to end.

## Troubleshooting

- If Python is not found, create a virtual environment or install Python 3.14+ on your system.
- If Webhook sending fails, check the GUI console output.

## Support

Report issues or suggestions to the GitHub Issue tracker.
