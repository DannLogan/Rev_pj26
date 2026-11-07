import pytest

from services.attendance_service import AttendanceService


class AttendanceRepository:
    def __init__(self, student=None, enrollment=None):
        self.student = student
        self.enrollment = enrollment
        self.updated = False

    def buscar_aluno_por_qr_token(self, token):
        return self.student

    def registrar_presenca_aluno(self, student_id, project_id, edition_id, professor_id):
        assert professor_id == 12
        if not self.enrollment:
            return "nao_inscrito"
        if self.enrollment["presenca"] == 1:
            return "ja_presente"
        self.enrollment["presenca"] = 1
        self.updated = True
        return "sucesso"


def test_professor_registra_presenca_de_aluno_inscrito():
    repository = AttendanceRepository(student={"id": 7, "nome": "Ana"}, enrollment={"presenca": 0})

    result = AttendanceService(repository).register_from_qr("qr-1", 3, 9, 12)

    assert result == {"status": "sucesso", "student": {"id": 7, "nome": "Ana"}}
    assert repository.updated is True


def test_segunda_leitura_nao_duplica_presenca():
    repository = AttendanceRepository(student={"id": 7}, enrollment={"presenca": 1})

    result = AttendanceService(repository).register_from_qr("qr-1", 3, 9, 12)

    assert result["status"] == "ja_presente"
    assert repository.updated is False


def test_aluno_nao_inscrito_nao_recebe_presenca():
    repository = AttendanceRepository(student={"id": 7}, enrollment=None)

    result = AttendanceService(repository).register_from_qr("qr-1", 3, 9, 12)

    assert result["status"] == "nao_inscrito"


def test_qr_inexistente_e_rejeitado():
    repository = AttendanceRepository(student=None)

    with pytest.raises(ValueError, match="QR code inválido"):
        AttendanceService(repository).register_from_qr("unknown", 3, 9, 12)
