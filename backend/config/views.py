from django.http import JsonResponse


def backend_status(request):
    """Confirma que o backend está ativo sem depender da interface React."""
    return JsonResponse({
        "aplicacao": "Estoque Veloz",
        "status": "online",
        "api": "/api/",
        "admin": "/admin/",
    })
