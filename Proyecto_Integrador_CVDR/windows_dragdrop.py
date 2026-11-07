"""Arrastrar y soltar archivos de Windows sobre un widget Tk/CustomTkinter."""
import ctypes
import sys
from ctypes import wintypes


class WindowsFileDrop:
    """Registra WM_DROPFILES sobre el widget recibido y entrega las rutas."""

    WM_DROPFILES = 0x0233
    GWL_WNDPROC = -4
    MSGFLT_ALLOW = 1

    def __init__(self, widget, callback):
        self.widget = widget
        self.callback = callback
        self.hwnd = None
        self._old_proc = None
        self._proc = None
        self._enabled = False

        if sys.platform != "win32":
            return

        try:
            self.hwnd = wintypes.HWND(int(widget.winfo_id()))
            user32 = ctypes.windll.user32
            shell32 = ctypes.windll.shell32

            shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
            shell32.DragAcceptFiles.restype = None
            shell32.DragAcceptFiles(self.hwnd, True)

            # Permite WM_DROPFILES incluso si la aplicación fue ejecutada
            # con un nivel de privilegios distinto al Explorador de Windows.
            try:
                change_filter = user32.ChangeWindowMessageFilterEx
                change_filter.argtypes = [
                    wintypes.HWND,
                    wintypes.UINT,
                    wintypes.DWORD,
                    ctypes.c_void_p,
                ]
                change_filter.restype = wintypes.BOOL
                change_filter(
                    self.hwnd,
                    self.WM_DROPFILES,
                    self.MSGFLT_ALLOW,
                    None,
                )
            except AttributeError:
                pass

            if ctypes.sizeof(ctypes.c_void_p) == 8:
                get_proc = user32.GetWindowLongPtrW
                set_proc = user32.SetWindowLongPtrW
            else:
                get_proc = user32.GetWindowLongW
                set_proc = user32.SetWindowLongW

            get_proc.argtypes = [wintypes.HWND, ctypes.c_int]
            get_proc.restype = ctypes.c_void_p
            set_proc.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
            set_proc.restype = ctypes.c_void_p

            call_window_proc = user32.CallWindowProcW
            call_window_proc.argtypes = [
                ctypes.c_void_p,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            call_window_proc.restype = wintypes.LRESULT

            WNDPROC = ctypes.WINFUNCTYPE(
                wintypes.LRESULT,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )

            self._old_proc = get_proc(self.hwnd, self.GWL_WNDPROC)

            @WNDPROC
            def wnd_proc(hwnd, msg, wparam, lparam):
                if msg == self.WM_DROPFILES:
                    try:
                        self._handle_drop(wparam)
                    finally:
                        shell32.DragFinish(wparam)
                    return 0

                return call_window_proc(
                    self._old_proc,
                    hwnd,
                    msg,
                    wparam,
                    lparam,
                )

            # Es indispensable conservar la referencia Python al callback.
            self._proc = wnd_proc
            set_proc(
                self.hwnd,
                self.GWL_WNDPROC,
                ctypes.cast(self._proc, ctypes.c_void_p),
            )

            # Evita que el callback sea recolectado mientras exista el widget.
            widget._windows_file_drop = self
            self._enabled = True

        except Exception as error:
            print(f"No se pudo activar Drag & Drop: {error}")
            self._enabled = False

    def _handle_drop(self, hdrop):
        shell32 = ctypes.windll.shell32
        shell32.DragQueryFileW.argtypes = [
            wintypes.HANDLE,
            wintypes.UINT,
            wintypes.LPWSTR,
            wintypes.UINT,
        ]
        shell32.DragQueryFileW.restype = wintypes.UINT

        count = shell32.DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
        paths = []

        for index in range(count):
            length = shell32.DragQueryFileW(hdrop, index, None, 0)
            buffer = ctypes.create_unicode_buffer(length + 1)
            shell32.DragQueryFileW(hdrop, index, buffer, length + 1)
            paths.append(buffer.value)

        if paths:
            self.callback(paths)

    @property
    def enabled(self):
        return self._enabled
