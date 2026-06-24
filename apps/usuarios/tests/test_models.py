import pytest
from django.contrib.auth.hashers import Argon2PasswordHasher
from django.db.utils import IntegrityError
from django.utils import timezone
from datetime import timedelta
from apps.usuarios.models import Usuario


class TestUsuarioModel:
    def test_crear_usuario_exitoso(self, db):
        usuario = Usuario.objects.create_user(
            email="test@example.com",
            nombre="Test User",
            rol=Usuario.Rol.VENDEDOR,
            password="SecurePass123!",
        )
        assert usuario.email == "test@example.com"
        assert usuario.nombre == "Test User"
        assert usuario.rol == Usuario.Rol.VENDEDOR
        assert usuario.activo is True
        assert usuario.is_staff is False
        assert usuario.is_superuser is False
        assert usuario.intentos_fallidos == 0
        assert usuario.bloqueado_hasta is None
        assert usuario.pk is not None

    def test_email_es_obligatorio(self, db):
        with pytest.raises(ValueError, match="El email es obligatorio"):
            Usuario.objects.create_user(
                email="",
                nombre="Sin Email",
                rol=Usuario.Rol.VENDEDOR,
                password="Pass123!",
            )

    def test_email_unico(self, db):
        Usuario.objects.create_user(
            email="duplicado@test.com",
            nombre="Primero",
            rol=Usuario.Rol.VENDEDOR,
            password="Pass123!",
        )
        with pytest.raises(IntegrityError):
            Usuario.objects.create_user(
                email="duplicado@test.com",
                nombre="Segundo",
                rol=Usuario.Rol.VENDEDOR,
                password="Pass456!",
            )

    def test_password_se_hashea_con_argon2(self, db):
        usuario = Usuario.objects.create_user(
            email="hash@test.com",
            nombre="Hash Test",
            rol=Usuario.Rol.ALMACENISTA,
            password="MyPassword123!",
        )
        assert usuario.password != "MyPassword123!"
        assert usuario.password.startswith(Argon2PasswordHasher.algorithm)

    def test_str_representation(self, db):
        usuario = Usuario.objects.create_user(
            email="str@test.com",
            nombre="Nombre Test",
            rol=Usuario.Rol.ADMINISTRADOR,
            password="Pass123!",
        )
        assert str(usuario) == "Nombre Test <str@test.com>"

    def test_esta_bloqueado_cuando_fecha_futura(self, db):
        usuario = Usuario.objects.create_user(
            email="bloqueado@test.com",
            nombre="Bloqueado",
            rol=Usuario.Rol.VENDEDOR,
            password="Pass123!",
        )
        usuario.bloqueado_hasta = timezone.now() + timedelta(hours=1)
        assert usuario.esta_bloqueado is True

    def test_no_esta_bloqueado_sin_fecha(self, db):
        usuario = Usuario.objects.create_user(
            email="no_bloqueado@test.com",
            nombre="No Bloqueado",
            rol=Usuario.Rol.VENDEDOR,
            password="Pass123!",
        )
        assert usuario.bloqueado_hasta is None
        assert usuario.esta_bloqueado is False

    def test_no_esta_bloqueado_si_fecha_pasada(self, db):
        usuario = Usuario.objects.create_user(
            email="ex_bloqueado@test.com",
            nombre="Ex Bloqueado",
            rol=Usuario.Rol.VENDEDOR,
            password="Pass123!",
        )
        usuario.bloqueado_hasta = timezone.now() - timedelta(hours=1)
        assert usuario.esta_bloqueado is False

    def test_save_resetea_intentos_al_desbloquear(self, db):
        usuario = Usuario.objects.create_user(
            email="desbloqueo@test.com",
            nombre="Desbloqueo",
            rol=Usuario.Rol.VENDEDOR,
            password="Pass123!",
        )
        usuario.intentos_fallidos = 5
        usuario.bloqueado_hasta = timezone.now() + timedelta(hours=1)
        usuario.save()
        usuario.intentos_fallidos = 5
        usuario.bloqueado_hasta = None
        usuario.save()
        usuario.refresh_from_db()
        assert usuario.intentos_fallidos == 0

    def test_create_superuser_es_staff_y_superuser(self, db):
        admin = Usuario.objects.create_superuser(
            email="super@test.com",
            nombre="Super Admin",
            password="SuperPass123!",
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.rol == Usuario.Rol.ADMINISTRADOR

    def test_rol_choices_validos(self, db):
        for rol_value, _ in Usuario.Rol.choices:
            usuario = Usuario.objects.create_user(
                email=f"{rol_value.lower()}@test.com",
                nombre=f"Rol {rol_value}",
                rol=rol_value,
                password="Pass123!",
            )
            assert usuario.rol == rol_value

    def test_user_model_usa_email_como_username_field(self):
        assert Usuario.USERNAME_FIELD == "email"

    def test_nombre_max_length(self):
        field = Usuario._meta.get_field("nombre")
        assert field.max_length == 150

    def test_email_unique_constraint(self):
        field = Usuario._meta.get_field("email")
        assert field.unique is True

    def test_permisos_personalizados_definidos(self):
        permisos = Usuario._meta.permissions
        codigos = [p[0] for p in permisos]
        assert "puede_ajustar_stock" in codigos
        assert "puede_ver_auditoria_completa" in codigos
        assert "puede_gestionar_usuarios" in codigos
        assert "puede_configurar_crm" in codigos
