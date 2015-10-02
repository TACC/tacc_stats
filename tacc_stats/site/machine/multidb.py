import threading
import logging
from django.http import Http404
from tacc_stats import cfg
logger = logging.getLogger('default')
request_cfg = threading.local()

class MultiDbRouterMiddleware (object):
    """
    The Multidb router middelware.

    he middleware process_view (or process_request) function sets some context
    from the URL into thread local storage, and process_response deletes it. In
    between, any database operation will call the router, which checks for this
    context and returns an appropriate database alias.
    """
    def process_view( self, request, view_func, args, kwargs ):
        if 'resource_name' in kwargs:
            request_cfg.resource_name = kwargs['resource_name']
            logger.debug( 'Resouce requested: %s. Saving it as a thread local variable.', request_cfg.resource_name )
            request.SELECTED_DATABASE = request_cfg.resource_name
            logger.debug( 'Setting config machine name as: %s', request_cfg.resource_name )
    def process_response( self, request, response ):
        if hasattr( request_cfg, 'resource_name' ):
            del request_cfg.resource_name
            logger.debug( 'Thread local variable resource_name deleted.' )
        return response

class MultiDbRouter(object):
    """
    The multiple database router.

    Add this to your Django database router configuration.
    """
    def _multi_db(self):
        from django.conf import settings
        if hasattr(request_cfg, 'resource_name'):
            logger.debug( 'Resouce requested: %s', request_cfg.resource_name )
            if request_cfg.resource_name in settings.DATABASES:
                logger.debug( 'Requested resource is valid.' )
                return request_cfg.resource_name
            else:
                logger.debug( 'Invalid resource requested.' )
                raise Http404
        else:
            logger.debug( 'Resource name is required.' )
            raise Http404

    def db_for_read(self, model, **hints):
        return self._multi_db()

    db_for_write = db_for_read