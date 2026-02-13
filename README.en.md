[README.en.md](https://github.com/user-attachments/files/25292635/README.en.md)
# vrcsol

Sol's RNG monitoring to VRChat and Discord Webhook integration GUI application.

## Requirements

- Windows 10 / 11 (64-bit recommended)
- Python 3.14 or later (when running from source)

The distribution structure consists of the root folder containing README and the Start GUI shortcut, with all source files located in the `source` subfolder.

## How to Run

### Recommended: Start from Shortcut

Double-click the "Start GUI" shortcut in the root folder.

On the first run, the virtual environment will be automatically created and required packages will be installed.

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

### Manual Virtual Environment Setup

The virtual environment is automatically set up on first run, but you can also set it up manually:

```powershell
cd .\source
.\setup.bat
```

### Development: Run from Source

```powershell
cd .\source
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r ..\requirements.txt
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
