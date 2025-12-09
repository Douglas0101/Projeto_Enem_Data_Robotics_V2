
from enem_project.domain.auth_schemas import UserCreate
from enem_project.services.auth_service import AuthService
from enem_project.infra.logging import logger

def create_admin():
    logger.info("Iniciando criação de usuário admin...")
    service = AuthService()
    
    email = "admin@enem.data"
    password = "AdminStrongPassword123!" 
    
    logger.info(f"Tentando criar usuário: {email}")
    
    try:
        # Verifica se já existe para dar feedback melhor
        existing = service.get_user_by_email(email)
        if existing:
            logger.warning(f"Usuário {email} já existe.")
            print(f"AVISO: Usuário {email} já existe no banco de dados.")
            return

        user = service.create_user(
            UserCreate(
                email=email,
                password=password,
                role="admin"
            )
        )
        logger.info(f"Usuário admin criado com sucesso: {user.email} (ID: {user.id})")
        print("-" * 40)
        print("SUCESSO: Admin criado.")
        print(f"Email: {email}")
        print(f"Senha: {password}")
        print("-" * 40)
    except Exception as e:
        logger.error(f"Erro ao criar admin: {e}")
        print(f"ERRO FATAL: {e}")

if __name__ == "__main__":
    create_admin()
