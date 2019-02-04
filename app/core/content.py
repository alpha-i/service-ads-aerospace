from flask import make_response, render_template, jsonify, g


class ApiResponse:
    def __init__(self, content_type, next=None, template=None, context=None, status_code=200):
        """
        A generic response for the API endpoints.

        It should dynamically select the best response type and format depending on the
        request mimetypes.

        :param str content_type: the mimetype for the format accepted by the client
        :param str next: an URL to redirect to
        :param str template: the path to a template to use for the HTML response
        :param dict context: the context to serialize or render in the template
        :param int status_code: the status code of the response
        """
        if content_type in ['text/html', 'application/html']:
            response = make_response(jsonify(context))  # TODO: changeme, needs a content type serializer
            response.status_code = status_code
            if template:
                if not context:
                    context = {}
                if g.get('user'):
                    context['profile'] = {'email': g.user.email}
                response = make_response(render_template(template, **context), status_code)
            if next:
                response.status_code = 302
                response.headers.add('Location', next)
            if template and next:
                response.status_code = 200
                response.headers.add('Refresh', f'5; url={next}')
        else:
            response = make_response(jsonify(context) if context else '', status_code)
            if next:
                response.headers.add('Location', next)

        self.response = response

    def __call__(self, *args, **kwargs):
        return self.response

    def set_cookie(self, key, value, expires):
        self.response.set_cookie(key, value, expires=expires)
