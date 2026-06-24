from django.db import transaction


def ejecutar_en_transaccion(func, *args, **kwargs):
    with transaction.atomic():
        return func(*args, **kwargs)
