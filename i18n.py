# i18n.py
# Copyright (c) 2025 Mehdi Rajabi. See LICENSE for details.

import gettext
import os
import logging
from database import db_manager

APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOCALE_DIR = os.path.join(APP_DIR, 'locale')

SUPPORTED_LANGUAGES = ['en', 'fa']
DEFAULT_LANGUAGE = 'en'

_ = None


def set_language(lang_code: str = None):
    """
    Sets the application's active language.

    Args:
        lang_code: The language code (e.g., 'en', 'fa'). If None, loads from DB.
    """
    global _

    if not lang_code:
        try:
            lang_code = db_manager.get_setting('language')
            if lang_code not in SUPPORTED_LANGUAGES:
                lang_code = DEFAULT_LANGUAGE
        except Exception as e:
            logging.warning(f"Could not load language from DB. Defaulting to 'en'. Error: {e}")
            lang_code = DEFAULT_LANGUAGE

    try:
        t = gettext.translation('base', localedir=LOCALE_DIR, languages=[lang_code], fallback=True)
        _ = t.gettext
    except FileNotFoundError:
        logging.warning(f"Translation file not found for lang '{lang_code}'. Using default text.")
        _ = lambda s: s


set_language()


def switch_language(lang_code: str):
    """
    Updates the language setting in the database and re-initializes the translator.

    Args:
        lang_code: The new language code to apply.
    """
    if lang_code in SUPPORTED_LANGUAGES:
        db_manager.set_setting('language', lang_code)
        set_language(lang_code)
        logging.info(f"Language switched to {lang_code}. App restart may be required.")
    else:
        logging.error(f"Unsupported language code '{lang_code}'.")