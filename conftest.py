from _pytest._io.terminalwriter import TerminalWriter

_orig_flush = TerminalWriter.flush

def _safe_flush(self, *args, **kwargs):
    try:
        return _orig_flush(self, *args, **kwargs)
    except OSError as e:
        if e.errno == 9:  # Bad file descriptor
            return
        raise

TerminalWriter.flush = _safe_flush
