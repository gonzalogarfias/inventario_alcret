def sanitizar_celda(valor):
    """Sanitiza un valor para prevenir inyección de fórmulas CSV/Excel.

    Antepone una comilla simple si el valor comienza con caracteres
    que Excel/Google Sheets interpretarían como fórmula.
    """
    s = str(valor)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + s
    return s
