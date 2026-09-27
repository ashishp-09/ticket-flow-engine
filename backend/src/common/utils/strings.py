import re


def camel_to_snake(name: str) -> str:
    return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()


def pluralize_eng(word: str) -> str:
    if word.endswith(('s', 'x', 'z', 'ch', 'sh')):
        return f"{word}es"
    elif word.endswith('y') and len(word) > 1 and word[-2] not in 'aeiou':
        return f"{word[:-1]}ies"
    elif word.endswith('fe'):
        return f"{word[:-2]}ves"
    elif word.endswith('f') and not word.endswith('ff'):
        return f"{word[:-1]}ves"
    return f"{word}s"
