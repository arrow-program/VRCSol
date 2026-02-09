import sys
try:
    import tkinter
    print('TK_OK', getattr(tkinter, 'TkVersion', 'unknown'))
except Exception as e:
    print('TK_ERR', repr(e))
    import traceback
    traceback.print_exc()
print('PYTHON:', sys.executable)
