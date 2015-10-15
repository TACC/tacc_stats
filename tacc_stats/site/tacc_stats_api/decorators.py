#
# NOT IN USE
#
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from tacc_stats_api.models import Token

def token_required(func):
    def inner(request, *args, **kwargs):
        if request.method == 'OPTIONS':
            return func(request, *args, **kwargs)
        auth_header = request.META.get('HTTP_AUTHORIZATION', None)
        if auth_header is not None:
            tokens = auth_header.split(' ')
            if len(tokens) == 2 and tokens[0] == 'Token':
                token = tokens[1]
                try:
                    request.token = Token.objects.get(token=token)
                    return func(request, *args, **kwargs)
                except Token.DoesNotExist:
                    return HttpResponseForbidden('Bad Authorization Token')
        return HttpResponseBadRequest('Missing Authorization')

    return inner
