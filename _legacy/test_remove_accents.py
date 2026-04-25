import unicodedata

def remove_accents(text):
    """Remove accents from text: autoliquidación -> autoliquidacion"""
    nfkd = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in nfkd if not unicodedata.combining(c))

text = "autoliquidación es el procedimiento"
print(f"Original: {text}")
print(f"Without accents: {remove_accents(text)}")

text2 = "El contribuyente que obtenga rendimientos del trabajo"
print(f"\nOriginal: {text2}")
print(f"Without accents: {remove_accents(text2)}")
