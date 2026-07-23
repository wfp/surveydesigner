from rest_framework.request import Request


class OrganizationMiddleware:
    """
    Middleware accepting `Survey-Designer-Organizations` http header,
    with list of organization's ids (comma delimited), converting it to request parameter
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: Request):
        organizations_header = request.headers.get("survey-designer-organizations", "")

        try:
            organizations = list(
                dict.fromkeys(
                    int(organization_id_str)
                    for organization_id_str in organizations_header.split(",")
                    if organizations_header
                )
            )
        except ValueError:
            organizations = []
            request.organization_ids_parse_error = True
        else:
            request.organization_ids_parse_error = False
        request.organization_ids = organizations
        if not request.organization_ids_parse_error:
            request.META["HTTP_SURVEY_DESIGNER_ORGANIZATIONS"] = ",".join(
                str(organization_id) for organization_id in sorted(organizations)
            )

        return self.get_response(request)
