import os
import sys
import subprocess

def run_build():
    """Compiles the Pink Transcribe Python application into a standalone desktop executable."""
    print("Preparing PyInstaller build configuration for Pink Transcribe...")
    
    # 1. Ensure PyInstaller is installed
    try:
        import PyInstaller
    except ImportError:
        print("PyInstaller is not installed in the current environment.")
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        
    import PyInstaller.__main__
    
    # 2. Configure pathing
    script_dir = os.path.dirname(os.path.abspath(__file__))
    entry_point = os.path.join(script_dir, "main.py")
    
    # Locate UI style resource and app icon to bundle as data files
    # Format: src_path;dest_subfolder (on Windows) or src_path:dest_subfolder (on Unix)
    sep = ";" if sys.platform.startswith("win") else ":"
    style_src = os.path.join(script_dir, "app", "ui", "styles.qss")
    style_dest = "app/ui"
    data_arg = f"{style_src}{sep}{style_dest}"
    
    icon_src = os.path.join(script_dir, "app", "ui", "app_icon.jpg")
    icon_dest = "app/ui"
    icon_data_arg = f"{icon_src}{sep}{icon_dest}"
    
    # Locate faster_whisper assets (VAD models) to bundle them inside the compiled package
    import faster_whisper
    fw_path = os.path.dirname(faster_whisper.__file__)
    fw_assets_src = os.path.join(fw_path, "assets")
    fw_assets_dest = "faster_whisper/assets"
    fw_data_arg = f"{fw_assets_src}{sep}{fw_assets_dest}"
    
    # Locate CUDA DLLs (cublas and cudnn) if available
    cuda_data_args = []
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
                cuda_data_args.append(f"--add-data={cublas_bin}{sep}nvidia/cublas/bin")
                print(f"Found CUDA cublas DLLs in: {cublas_bin}")
        if cudnn_dir:
            cudnn_bin = os.path.join(cudnn_dir, "bin")
            if os.path.exists(cudnn_bin):
                cuda_data_args.append(f"--add-data={cudnn_bin}{sep}nvidia/cudnn/bin")
                print(f"Found CUDA cudnn DLLs in: {cudnn_bin}")
    except ImportError:
        print("CUDA wheel packages not found. Building without bundled CUDA DLLs.")
    
    # 3. Assemble PyInstaller parameters
    args = [
        entry_point,
        "--name=PinkTranscribe",
        # Use onedir (directory-based distribution) instead of onefile.
        # This is strongly recommended for machine learning apps because:
        # 1. Start time is instant (no temp-file unpacking of 200MB+ dlls).
        # 2. HuggingFace tokenizers and ctranslate2 dlls resolve paths predictably.
        "--onedir",
        "--console",  # Enabled for safe C++ log handles (hidden programmatically in main.py)
        f"--add-data={data_arg}",
        f"--add-data={icon_data_arg}",
        f"--add-data={fw_data_arg}",
    ] + cuda_data_args + [
        # Add hidden imports that are loaded dynamically by dependencies
        "--hidden-import=sounddevice",
        "--hidden-import=faster_whisper",
        "--hidden-import=PySide6.QtCore",
        "--hidden-import=PySide6.QtWidgets",
        "--hidden-import=PySide6.QtGui",
        "--clean",
        "--noconfirm",
    ]
    
    print(f"Running PyInstaller with arguments: {args}")
    try:
        PyInstaller.__main__.run(args)
        print("\nBuild completed successfully!")
        print(f"Executable directory can be found at: {os.path.join(script_dir, 'dist', 'PinkTranscribe')}")
    except Exception as e:
        print(f"\nBuild failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    run_build()
