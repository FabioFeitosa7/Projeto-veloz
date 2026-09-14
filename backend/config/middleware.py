from django.core.exceptions import RequestDataTooBig
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class LimitePayloadApiMiddleware(MiddlewareMixin):
    """Retorna JSON quando uma requisição da API excede o limite configurado."""

    def process_exception(self, request, exception):
        if request.path.startswith("/api/") and isinstance(exception, RequestDataTooBig):
            return JsonResponse(
                {"detail": "A requisição excede o tamanho máximo permitido."},
                status=413,
            )
        return None
