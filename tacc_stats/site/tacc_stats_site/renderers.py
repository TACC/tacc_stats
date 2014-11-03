from rest_framework.renderers import JSONRenderer

class TACCJSONRenderer(JSONRenderer):
    media_type = 'application/json'
    format = 'json'

    def render(self, data, media_type=None, renderer_context=None):
        data = {'status':'success','result': data,'message':''}
        return super(TACCJSONRenderer, self).render(data, media_type, renderer_context)
