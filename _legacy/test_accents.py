import re
import unicodedata

def _add_accents(text: str) -> str:
    accent_fixes = {
        'autoliquidacion': 'autoliquidación',
        'declaracion': 'declaración',
        'procedimiento': 'procedimiento',
        'tributario': 'tributario',
        'administracion': 'administración',
        'resolucion': 'resolución',
        'prescripcion': 'prescripción',
        'contabilidad': 'contabilidad',
    }
    words = re.findall(r"[\w]+", text.lower())
    result = text
    for word in words:
        if word in accent_fixes:
            result = result.replace(word, accent_fixes[word])
    return result

# Test
print(_add_accents("autoliquidacion"))
print(_add_accents("IRPF modelo 100"))
print(_add_accents("IVA libros"))
print(_add_accents("autoliquidación"))
