from lingua import LanguageDetectorBuilder
import argostranslate.translate
import argostranslate.package
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

# Initialise detector once, rather than on every translation.
_detector = LanguageDetectorBuilder.from_all_languages().build()

# TODO: Implement this into the chat, so it can translate messages for users.
def translate_message(
    message: str,
    target: str,
    source: str = "auto"
) -> str:
    """
    Translate text using Argos Translate.

    Args:
        message: Text to translate.
        target: Target language ISO 639-1 code (e.g. 'en', 'ja').
        source: Source language code, or 'auto' for detection.

    Returns:
        Translated text.

    Raises:
        ValueError: Invalid language or undetectable language.
        RuntimeError: Translation model unavailable or installation failed.
    """

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Message cannot be empty.")

    target = target.lower().strip()
    source = source.lower().strip()

    # Detect source language.
    if source == "auto":
        detected = _detector.detect_language_of(message)

        if detected is None:
            raise ValueError("Could not detect source language.")

        source = detected.iso_code_639_1.name.lower()

    # No translation necessary.
    if source == target:
        return message

    # Refresh available language packages.
    installed = argostranslate.translate.get_installed_languages()

    def has_translation(src, dst):
        languages = argostranslate.translate.get_installed_languages()

        source_lang = next(
            (lang for lang in languages if lang.code == src), None
        )

        target_lang = next(
            (lang for lang in languages if lang.code == dst), None
        )

        if source_lang is None or target_lang is None:
            return False

        return source_lang.get_translation(target_lang) is not None

    # Install missing translation models.
    if not has_translation(source, target):
        try:
            argostranslate.package.update_package_index()

            success = argostranslate.package.install_package_for_language_pair(
                source,
                target
            )

            if not success:
                raise RuntimeError(
                    f"No translation package available: {source} -> {target}"
                )

        except Exception as exc:
            raise RuntimeError(
                f"Failed to install translation package: {exc}"
            ) from exc

    # Translate.
    try:
        return argostranslate.translate.translate(
            message,
            source,
            target
        )

    except Exception as exc:
        raise RuntimeError(
            f"Translation failed ({source} -> {target}): {exc}"
        ) from exc
