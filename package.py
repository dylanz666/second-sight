import subprocess
import sys


def main():
    print("Starting build process...")
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--windowed",
        "--name=千里眼(远程桌面)",
        "--icon=icon.ico",
        "main.py",
    ]
    print(" ".join(cmd))
    try:
        result = subprocess.run(cmd, check=True)
        print("Build completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
