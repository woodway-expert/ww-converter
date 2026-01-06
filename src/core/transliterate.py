"""
Ukrainian to Latin transliteration module.
Based on Ukrainian national standard (scientific transliteration).
"""

# Ukrainian to Latin transliteration map
UA_TO_LATIN = {
    # Uppercase
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'H', 'Ґ': 'G',
    'Д': 'D', 'Е': 'E', 'Є': 'Ye', 'Ж': 'Zh', 'З': 'Z',
    'И': 'Y', 'І': 'I', 'Ї': 'Yi', 'Й': 'Y', 'К': 'K',
    'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O', 'П': 'P',
    'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F',
    'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Shch',
    'Ь': '', 'Ю': 'Yu', 'Я': 'Ya',
    # Lowercase
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'h', 'ґ': 'g',
    'д': 'd', 'е': 'e', 'є': 'ye', 'ж': 'zh', 'з': 'z',
    'и': 'y', 'і': 'i', 'ї': 'yi', 'й': 'y', 'к': 'k',
    'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p',
    'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f',
    'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
    'ь': '', 'ю': 'yu', 'я': 'ya',
    # Russian letters (for compatibility)
    'Ы': 'Y', 'ы': 'y', 'Э': 'E', 'э': 'e',
    'Ё': 'Yo', 'ё': 'yo', 'Ъ': '', 'ъ': '',
    # Apostrophe
    "'": '', "'": '', "ʼ": '',
}


def transliterate_ua(text: str) -> str:
    """
    Transliterate Ukrainian text to Latin characters.
    
    Args:
        text: Ukrainian text to transliterate
        
    Returns:
        Transliterated text in Latin characters
    """
    result = []
    for char in text:
        if char in UA_TO_LATIN:
            result.append(UA_TO_LATIN[char])
        elif char.isascii():
            result.append(char)
        else:
            # Skip unknown characters
            pass
    return ''.join(result)


def to_seo_slug(text: str) -> str:
    """
    Convert text to SEO-friendly slug.
    - Transliterates Ukrainian to Latin
    - Converts to lowercase
    - Replaces spaces with hyphens
    - Removes special characters
    - Collapses multiple hyphens
    
    Args:
        text: Text to convert
        
    Returns:
        SEO-friendly slug
    """
    # Transliterate
    text = transliterate_ua(text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and underscores with hyphens
    text = text.replace(' ', '-').replace('_', '-')
    
    # Keep only alphanumeric and hyphens
    result = []
    for char in text:
        if char.isalnum() or char == '-' or char == '.':
            result.append(char)
    text = ''.join(result)
    
    # Collapse multiple hyphens
    while '--' in text:
        text = text.replace('--', '-')
    
    # Strip leading/trailing hyphens
    text = text.strip('-')
    
    return text


if __name__ == "__main__":
    # Test examples
    test_cases = [
        "Шпон дуб натуральний",
        "Фанера ФСФ березова 18мм",
        "Струганий шпон",
        "Кореневі зрізи горіха",
        "МДФ плита шпонована",
    ]
    
    for test in test_cases:
        print(f"{test} -> {to_seo_slug(test)}")
