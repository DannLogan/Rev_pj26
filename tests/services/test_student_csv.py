import pytest

from services.student_csv import read_student_csv


@pytest.mark.parametrize("separator", [";", ",", "\t"])
def test_importacao_aceita_cabecalho_excel_e_preserva_zeros(separator):
    header = separator.join(["Matrícula / RA", "Nome", "E-mail"])
    row = separator.join(["0000000123", '"Silva, Ana"', ""])
    assert read_student_csv(f"{header}\r\n\r\n{row}\r\n".encode("utf-8-sig")) == [
        (3, ["0000000123", "Silva, Ana", ""])
    ]


def test_importacao_aceita_utf16_sem_cabecalho():
    assert read_student_csv("0000000123\tJoão\n".encode("utf-16")) == [(1, ["0000000123", "João"])]


def test_importacao_aceita_diretiva_excel():
    assert read_student_csv(b"sep=,\nRA,Nome\n0000000123,Ana\n") == [(3, ["0000000123", "Ana"])]


def test_importacao_remove_virgulas_nas_pontas_sem_alterar_as_internas():
    assert read_student_csv(b'RA;Nome\n0000000123;", Silva, Ana ,"\n') == [
        (2, ["0000000123", "Silva, Ana"])
    ]


def test_importacao_informa_csv_com_aspas_incompletas():
    with pytest.raises(ValueError, match="linha 2"):
        read_student_csv(b'RA;Nome\n0000000123;"Ana')
