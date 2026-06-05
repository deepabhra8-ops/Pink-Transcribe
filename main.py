import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from app.ui.main_window import MainWindow
from app.utils.logger import logger, LOG_FILE

def global_exception_hook(exctype, value, tb):
    """Intercepts and logs unhandled exceptions before graceful exit or notification."""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Unhandled exception encountered:\n{error_msg}")
    
    app = QApplication.instance()
    if app:
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("System Crash Detected")
            box.setText("An unexpected system error occurred.")
            box.setInformativeText(
                f"We apologize for the inconvenience. Details have been logged to the support file:\n\n"
                f"{LOG_FILE}\n\n"
                f"Error: {exctype.__name__}: {value}"
            )
            box.setStandardButtons(QMessageBox.Ok)
            box.exec()
        except Exception as e:
            print(f"Error drawing exception dialog box: {e}")
            
    sys.__excepthook__(exctype, value, tb)

import os
import ctypes

def setup_cuda_dlls():
    """Dynamically resolves and injects nvidia site-package DLL paths into Windows loading search path."""
    if sys.platform.startswith("win"):
        try:
            import nvidia.cublas
            import nvidia.cudnn
            
            def get_module_dir(module):
                if hasattr(module, "__path__") and module.__path__:
                    return list(module.__path__)[0]
                if hasattr(module, "__file__") and module.__file__:
                    return os.path.dirname(module.__file__)
                return None
                
            cublas_dir = get_module_dir(nvidia.cublas)
            cudnn_dir = get_module_dir(nvidia.cudnn)
            
            if cublas_dir:
                cublas_bin = os.path.join(cublas_dir, "bin")
                if os.path.exists(cublas_bin):
                    os.add_dll_directory(cublas_bin)
                    os.environ["PATH"] = cublas_bin + os.pathsep + os.environ["PATH"]
                    print(f"Added DLL directory: {cublas_bin}")
                
            if cudnn_dir:
                cudnn_bin = os.path.join(cudnn_dir, "bin")
                if os.path.exists(cudnn_bin):
                    os.add_dll_directory(cudnn_bin)
                    os.environ["PATH"] = cudnn_bin + os.pathsep + os.environ["PATH"]
                    print(f"Added DLL directory: {cudnn_bin}")
                
        except ImportError:
            # Silently ignore if not installed
            pass
        except Exception as e:
            print(f"Error setting up CUDA DLLs: {e}")

def hide_console():
    """Hides the console window on Windows immediately on startup."""
    if sys.platform.startswith("win"):
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            # SW_HIDE = 0
            ctypes.windll.user32.ShowWindow(hwnd, 0)

def main() -> None:
    """Application main initialization entrypoint."""
    setup_cuda_dlls()
    hide_console()
    
    # Windows taskbar grouping fix
    if sys.platform.startswith("win"):
        try:
            myappid = 'antigravity.pinktranscribe.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Failed to set AppUserModelID: {e}")
            
    sys.excepthook = global_exception_hook
    logger.info("Pink Transcribe application booting up...")
    
    app = QApplication(sys.argv)
    app.setApplicationName("PinkTranscribe")
    app.setOrganizationName("Antigravity")
    app.setApplicationVersion("1.0.0")
    
    # Set application icon globally
    from PySide6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(__file__), "app", "ui", "app_icon.jpg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    try:
        window = MainWindow()
        window.show()
        logger.info("Main Window initialized and presented.")
    except Exception as e:
        logger.critical(f"Failed to initialize MainWindow: {e}", exc_info=True)
        sys.exit(1)
        
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
