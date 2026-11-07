def linha_para_planilha(valores):
    """Preserva células comuns e trata valores que podem iniciar fórmulas."""
    return [
        "'" + valor
        if isinstance(valor, str) and valor.lstrip().startswith(("=", "+", "-", "@", "＝", "＋", "－", "＠"))
        else valor
        for valor in valores
    ]
