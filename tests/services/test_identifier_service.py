from services.identifier_service import format_next_identifier


def test_formata_proximo_identificador_com_base_no_maior_existente():
    assert format_next_identifier(["00001", "00009"], width=5) == "00010"


def test_inicia_identificador_quando_nao_ha_registros():
    assert format_next_identifier([], width=4) == "0001"
