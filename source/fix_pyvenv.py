#!/usr/bin/env python3
"""
Fix pyvenv.cfg to point to the current system Python.
This allows .venv to work across different user environments.
"""
import os
import sys

def fix_pyvenv_cfg():
    # Get the base Python installation (works even when called from venv)
    # sys.base_prefix points to the base Python, not the venv
    current_python_home = sys.base_prefix
    current_python_exe = os.path.join(current_python_home, 'python.exe')
    
    # Path to pyvenv.cfg
    venv_dir = os.path.join(os.path.dirname(__file__), '.venv')
    pyvenv_cfg = os.path.join(venv_dir, 'pyvenv.cfg')
    
    if not os.path.exists(pyvenv_cfg):
        print(f"[ERROR] pyvenv.cfg not found at {pyvenv_cfg}")
        return False
    
    try:
        # Read current config
        with open(pyvenv_cfg, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Update home and executable lines
        updated_lines = []
        for line in lines:
            if line.startswith('home = '):
                updated_lines.append(f'home = {current_python_home}\n')
            elif line.startswith('executable = '):
                updated_lines.append(f'executable = {current_python_exe}\n')
            else:
                updated_lines.append(line)
        
        # Write back
        with open(pyvenv_cfg, 'w', encoding='utf-8') as f:
            f.writelines(updated_lines)
        
        print(f"[OK] pyvenv.cfg updated to use: {current_python_exe}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to fix pyvenv.cfg: {e}")
        return False

if __name__ == '__main__':
    success = fix_pyvenv_cfg()
    sys.exit(0 if success else 1)
