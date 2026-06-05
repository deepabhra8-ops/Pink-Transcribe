import sys
import traceback
from PySide6.QtWidgets import QApplication, QMessageBox
from app.ui.main_window import MainWindow
from app.utils.logger import logger, LOG_FILE

def global_exception_hook(exctype, value, tb):
    """Intercepts and logs unhandled exceptions before graceful exit or notification."""
    error_msg = "".join(traceback.format_exception(exctype, value, tb))
    logger.critical(f"Unhandled exception encountered:\n{error_msg}")
    
    # Check if a QApplication instance exists to display visual alert
    app = QApplication.instance()
    if app:
        try:
            # Create user-friendly diagnostics error alert box
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
            
    # Forward exception to default system output
    sys.__excepthook__(exctype, value, tb)

def main() -> None:
    """Application main initialization entrypoint."""
    # Set exception hook
    sys.excepthook = global_exception_hook
    
    # Windows taskbar grouping fix
    import os
    if sys.platform.startswith("win"):
        try:
            import ctypes
            myappid = 'antigravity.pinktranscribe.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception as e:
            print(f"Failed to set AppUserModelID: {e}")
            
    logger.info("Pink Transcribe application booting up...")
    
    # Initialize QApplication
    app = QApplication(sys.argv)
    app.setApplicationName("PinkTranscribe")
    app.setOrganizationName("Antigravity")
    app.setApplicationVersion("1.0.0")
    
    # Set application icon globally
    from PySide6.QtGui import QIcon
    icon_path = os.path.join(os.path.dirname(__file__), "ui", "app_icon.jpg")
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    
    # Create and present Window
    try:
        window = MainWindow()
        window.show()
        logger.info("Main Window initialized and presented.")
    except Exception as e:
        logger.critical(f"Failed to initialize MainWindow: {e}", exc_info=True)
        sys.exit(1)
        
    # Execute App loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
