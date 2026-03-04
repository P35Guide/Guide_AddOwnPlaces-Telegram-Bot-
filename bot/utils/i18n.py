import json
import os
from pathlib import Path

class I18n:
    def __init__(self):
        self.translations = {}
        self.locales_path = Path(__file__).parent.parent.parent / "locales"
        self.user_lang_file = Path(__file__).parent / "user_languages.json"
        self.user_languages = {}
        self.default_lang = "uk"
        self.supported_langs = ["uk", "en", "de", "fr", "es", "it", "pl", "pt", "ja", "zh"]
        self._load_translations()
        self._load_user_languages()

    def normalize_lang(self, lang: str) -> str:
        normalized = lang.split("-")[0].lower() if lang else self.default_lang
        if normalized not in self.supported_langs:
            return self.default_lang
        return normalized

    def _load_translations(self):
        """Load all translation files"""
        for lang in self.supported_langs:
            lang_file = self.locales_path / f"{lang}.json"
            if lang_file.exists():
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        self.translations[lang] = json.load(f)
                except Exception as e:
                    print(f"Error loading {lang}.json: {e}")
                    self.translations[lang] = {}
            else:
                self.translations[lang] = {}

    def _load_user_languages(self):
        if not self.user_lang_file.exists():
            self.user_languages = {}
            return
        try:
            with open(self.user_lang_file, "r", encoding="utf-8") as file:
                data = json.load(file)
                self.user_languages = {str(k): self.normalize_lang(v) for k, v in data.items()}
        except Exception:
            self.user_languages = {}

    def _save_user_languages(self):
        try:
            with open(self.user_lang_file, "w", encoding="utf-8") as file:
                json.dump(self.user_languages, file, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def set_user_language(self, user_id: int, lang: str):
        self.user_languages[str(user_id)] = self.normalize_lang(lang)
        self._save_user_languages()

    def get_user_language(self, user_id: int, fallback_lang: str = None) -> str:
        stored_lang = self.user_languages.get(str(user_id))
        if stored_lang:
            return stored_lang
        return self.normalize_lang(fallback_lang or self.default_lang)

    def get(self, key: str, lang: str = None, **kwargs) -> str:
        """
        Get translation for a key
        
        Args:
            key: Translation key
            lang: Language code (defaults to uk)
            **kwargs: Format parameters for the string
            
        Returns:
            Translated string or key if not found
        """
        if lang is None:
            lang = self.default_lang
        
        # Normalize language code (e.g., "uk-UA" -> "uk")
        lang = self.normalize_lang(lang)
        
        # Use default language if requested language not supported
        if lang not in self.translations:
            lang = self.default_lang
        
        # Get translation
        translation = self.translations.get(lang, {}).get(key, key)
        
        # Format with kwargs if provided
        if kwargs:
            try:
                translation = translation.format(**kwargs)
            except KeyError:
                pass  # Return as is if formatting fails
        
        return translation

    def get_button_text(self, key: str, lang: str = None) -> str:
        """Get button text (same as get but for clarity)"""
        return self.get(key, lang)

    def get_all_buttons_variants(self, key: str) -> list:
        """Get all language variants for a button text"""
        variants = []
        for lang in self.supported_langs:
            text = self.get(key, lang)
            if text and text not in variants:
                variants.append(text)
        return variants

# Global instance
i18n = I18n()
