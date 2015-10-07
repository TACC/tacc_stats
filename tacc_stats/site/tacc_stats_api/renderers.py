from rest_framework.renderers import JSONRenderer
import logging

logger = logging.getLogger('default')
class TACCJSONRenderer(JSONRenderer):
    media_type = 'application/json'
    format = 'json'

    def render(self, data, media_type=None, renderer_context=None):
        return super(TACCJSONRenderer, self).render(data, media_type, renderer_context)
