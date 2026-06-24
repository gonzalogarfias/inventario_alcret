import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, rol, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio")
        email = self.normalize_email(email)
        usuario = self.model(email=email, nombre=nombre, rol=rol, **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, email, nombre, password=None):
        return self.create_user(
            email=email,
            nombre=nombre,
            rol=Usuario.Rol.ADMINISTRADOR,
            password=password,
            is_staff=True,
            is_superuser=True,
        )


class Usuario(AbstractBaseUser, PermissionsMixin):
    class Rol(models.TextChoices):
        ADMINISTRADOR = "ADMIN", "Administrador"
        VENDEDOR = "VENDEDOR", "Vendedor"
        ALMACENISTA = "ALMACEN", "Almacenista"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150)
    rol = models.CharField(max_length=20, choices=Rol.choices)
    activo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    intentos_fallidos = models.IntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        permissions = [
            ("puede_ajustar_stock", "Puede hacer ajustes y mermas"),
            ("puede_ver_auditoria_completa", "Puede ver auditoría completa"),
            ("puede_gestionar_usuarios", "Puede gestionar usuarios"),
            ("puede_configurar_crm", "Puede configurar integración CRM"),
        ]

    def __str__(self):
        return f"{self.nombre} <{self.email}>"

    def save(self, *args, **kwargs):
        if self.pk and Usuario.objects.filter(pk=self.pk).exists():
            original = Usuario.objects.get(pk=self.pk)
            if original.bloqueado_hasta != self.bloqueado_hasta:
                self.intentos_fallidos = 0
        super().save(*args, **kwargs)

    @property
    def esta_bloqueado(self):
        from django.utils import timezone
        if self.bloqueado_hasta and self.bloqueado_hasta > timezone.now():
            return True
        return False
