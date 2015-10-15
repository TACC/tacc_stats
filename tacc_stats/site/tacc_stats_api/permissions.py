from rest_framework.permissions import BasePermission

SAFE_METHODS = ['GET', 'HEAD', 'OPTIONS']

class IsAuthenticatedOrAdmin(BasePermission):
    """
    The request is authenticated for safe methods or admin for post and put
    """

    def has_permission(self, request, view):
        return (request.user and (request.user.is_staff or (request.method in SAFE_METHODS and request.user.is_authenticated())))

        