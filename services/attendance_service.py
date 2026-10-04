class AttendanceService:
    def __init__(self, repository):
        self.repository = repository

    def register_from_qr(self, qr_token: str, project_id: int, edition_id: str) -> dict:
        student = self.repository.buscar_aluno_por_qr_token(qr_token)
        if not student:
            raise ValueError("QR code inválido")

        status = self.repository.registrar_presenca_aluno(
            student["id"], project_id, edition_id
        )
        return {"status": status, "student": student}
