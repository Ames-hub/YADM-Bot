import platform
import sys

def get_os_name():
    system = platform.system()

    if system == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.strip().split("=", 1)[1].strip('"')
        except FileNotFoundError:
            return "Linux (unknown distro)"

    elif system == "Windows":
        ver = sys.getwindowsversion()
        return "Windows 11" if ver.build >= 22000 else "Windows 10"

    elif system == "Darwin":
        return f"macOS {platform.mac_ver()[0]}"

    return system