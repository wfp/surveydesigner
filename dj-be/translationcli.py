from deep_translator import GoogleTranslator

import json
import os
import sys
import time
from tabulate import tabulate

LOCALES_FOLDER = "survey_designer/apps/frontend/src/locales/"
CURRENT_SUPPORTED_LANGUAGES = (
    "ar",
    "fr",
    "es",
    "pt",
    "ru",
)


def translate_dict(input_dict, target_language="en"):
    translator = GoogleTranslator(source="auto", target=target_language)

    def recursive_translate(value):
        if isinstance(value, str):
            translated_value = translator.translate(value)
            return translated_value.strip()  # Remove trailing newline
        elif isinstance(value, dict):
            translated_dict = {}
            for key, val in value.items():
                translated_dict[key] = recursive_translate(val)
            return translated_dict
        elif isinstance(value, list):
            translated_list = []
            for item in value:
                translated_list.append(recursive_translate(item))
            return translated_list
        else:
            return value

    return recursive_translate(input_dict)


def load_english_as_json():
    """
    Loads `en/translation.json` into a Python dict.
    """

    with open(os.path.join(LOCALES_FOLDER, "en/translations.json")) as f:
        return json.load(f)


def save_translated_dict_as_json(
    translated_dict, language, filename="translations.json"
):
    """
    Saves the translated dict as a JSON file.
    """
    if language == None:
        raise ValueError("Language is not defined.")

    def dump():
        with open(file_path, "w") as f:
            json.dump(translated_dict, f, indent=2, ensure_ascii=False)

    file_path = os.path.join(LOCALES_FOLDER, f"{language}/{filename}")
    if os.path.exists(file_path):
        dump()
    else:
        os.mkdir(os.path.join(LOCALES_FOLDER, language))
        dump()


def run():
    input_dict = load_english_as_json()
    print(f"Saving Languages To: {LOCALES_FOLDER}")
    meta_data_array = []
    for language in CURRENT_SUPPORTED_LANGUAGES:
        success = False
        translate_start_time = time.time()
        try:
            translated_dict = translate_dict(input_dict, target_language=language)
            success = True
        except Exception as e:
            print(f"Failed to translate to {language}, json not saved: {e}, ")
            translated_dict = None

        translate_end_time = time.time()
        if not success or translated_dict == None:
            meta_data_array.append(
                [
                    language,
                    False,
                    translate_end_time - translate_start_time,
                    0,
                ]
            )
            continue
        save_start_time = time.time()
        save_translated_dict_as_json(translated_dict, language=language)
        save_end_time = time.time()

        meta_data_array.append(
            [
                language,
                True,
                translate_end_time - translate_start_time,
                save_end_time - save_start_time,
            ]
        )
    print(
        tabulate(
            meta_data_array,
            headers=[
                "Language",
                "Success",
                "Time to Translate (sec)",
                "Time to Save (sec)",
            ],
        )
    )


if __name__ == "__main__":

    if len(sys.argv) < 2:
        run()
    else:
        _, path = sys.argv[:2]
        # if path exists then overwrite locales folder.
        if path.startswith("--path="):
            path = path.split("=")[1]
        elif path.startswith("-p="):
            path = path.split("=")[1]
        elif path == "help":
            print("Usage: python translationcli.py [path]")
            print(
                "Example: python translationcli.py --path=survey_designer/apps/frontend/src/public/locales/"
            )
            print(
                f"If NO path is specified then the default path is used: {LOCALES_FOLDER}"
            )
            print(
                f"Default path can be changed by changing the LOCALES_FOLDER variable in the script."
            )
            print(
                f"The option to specify a path is to allow for the script to be tested outside the project locale folder."
            )
            print(f"\n\nSupported Languages: {CURRENT_SUPPORTED_LANGUAGES}")
            print(
                f"Current Supported Languages can be changed by changing the CURRENT_SUPPORTED_LANGUAGES variable in the script."
            )
            sys.exit(0)
        if os.path.exists(path):
            LOCALES_FOLDER = path
            run()
        else:
            print(f"Path {path} does not exist.")
            sys.exit(1)
