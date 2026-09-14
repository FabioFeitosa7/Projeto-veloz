from rest_framework.throttling import SimpleRateThrottle


class _ThrottlePorIp(SimpleRateThrottle):
    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class LeituraRateThrottle(_ThrottlePorIp):
    scope = "api_leitura"

    def allow_request(self, request, view):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            return True
        return super().allow_request(request, view)


class EscritaRateThrottle(_ThrottlePorIp):
    scope = "api_escrita"

    def allow_request(self, request, view):
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return True
        return super().allow_request(request, view)
