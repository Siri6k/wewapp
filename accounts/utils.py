import re


def normalize_phone(raw):
    """0812345678 -> +243812345678 ; 243812345678 -> +243812345678."""
    cleaned = re.sub(r"[^\d+]", "", raw or "")
    if cleaned.startswith("+"):
        return cleaned
    if cleaned.startswith("00"):
        return "+" + cleaned[2:]
    if cleaned.startswith("0"):
        return "+243" + cleaned[1:]
    if cleaned.startswith("243"):
        return "+" + cleaned
    return "+243" + cleaned
