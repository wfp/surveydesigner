from django_rq import job

from .send_email import EmailHelper


@job
def send_email(email_helper):
    """
    Send a generic mail belonging to EmailHelper class
    """
    if not isinstance(email_helper, EmailHelper):
        raise TypeError("Object passed is not an EmailHelper instance")
    email_helper.send_email()
    return f"Email correctly forwarded to {email_helper.to_list}"
