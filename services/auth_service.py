from utils.passwords import verify_password


def validar_nova_senha(usuario: dict, senha: str, confirmacao: str | None) -> str | None:
    if len(senha) < 12 or len(senha.encode("utf-8")) > 72:
        return "A senha deve ter pelo menos 12 caracteres e no máximo 72 bytes em UTF-8."
    if senha != confirmacao:
        return "A confirmação da senha deve ser igual à nova senha."
    if verify_password(usuario["senha"], senha):
        return "A nova senha deve ser diferente da senha provisória."
    if senha in (usuario["login"], usuario["matricula"], usuario["id_corporativo"]):
        return "A nova senha deve ser diferente dos seus identificadores de acesso."
    return None
