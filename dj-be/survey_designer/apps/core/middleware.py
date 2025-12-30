from rest_framework.request import Request


class OrganizationMiddleware:
    """
    Middleware accepting `Survey-Designer-Organizations` http header,
    with list of organization's ids (comma delimited), converting it to request parameter
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: Request):
        organizations = request.headers.get("survey-designer-organizations", "")

        try:
            organizations = [
                int(organization_id_str)
                for organization_id_str in set(organizations.split(","))
            ]
        except ValueError:
            organizations = []
        request.organization_ids = organizations

        return self.get_response(request)
