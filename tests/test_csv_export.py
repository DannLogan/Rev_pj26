from utils.csv_export import linha_para_planilha


def test_csv_planilha_trata_formulas_e_preserva_matricula():
    valores = ["=1+1", "  +1", "＠SUM(A1)", "000123", "Maria", None, 1]
    assert linha_para_planilha(valores) == [
        "'=1+1", "'  +1", "'＠SUM(A1)", "000123", "Maria", None, 1
    ]
