import os
import sys
import platform
import io


def fix_windows_console(prefer_utf8: bool = True, ignore_errors: bool = True) -> None:
    """Fix Windows console encoding to avoid GBK Unicode errors.

    - Prefer UTF-8 code page 65001 when possible (Windows 10+)
    - Reconfigure sys.stdout/stderr encoding
    - Optionally ignore encoding errors to avoid crashes
    """
    try:
        if platform.system() != 'Windows':
            return

        # Prefer UTF-8 code page
        if prefer_utf8:
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                # 65001 = UTF-8
                kernel32.SetConsoleOutputCP(65001)
                kernel32.SetConsoleCP(65001)
            except Exception:
                pass

        # Ensure Python IO uses UTF-8 or ignores errors
        encoding = 'utf-8' if prefer_utf8 else sys.getdefaultencoding() or 'utf-8'
        errors_mode = 'ignore' if ignore_errors else 'strict'

        # Python 3.7+: reconfigure available
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(encoding=encoding, errors=errors_mode)
            else:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors=errors_mode)
        except Exception:
            try:
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding=encoding, errors=errors_mode)
            except Exception:
                pass

        try:
            if hasattr(sys.stderr, 'reconfigure'):
                sys.stderr.reconfigure(encoding=encoding, errors=errors_mode)
            else:
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=encoding, errors=errors_mode)
        except Exception:
            try:
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding=encoding, errors=errors_mode)
            except Exception:
                pass

        # Hint Python to prefer UTF-8 for child processes
        os.environ.setdefault('PYTHONIOENCODING', f'{encoding}:{errors_mode}')

    except Exception:
        # As a last resort, ignore encoding errors to avoid crashing
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, errors='ignore')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, errors='ignore')
        except Exception:
            pass
