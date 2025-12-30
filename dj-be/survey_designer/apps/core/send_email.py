import logging

from django.conf import settings
from django.core.mail.message import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


class EmailHelper:
    def __init__(
        self, template, ctx, subject, to_list, bcc_list=None, replyto_list=None
    ):
        self.template = template
        self.ctx = ctx
        self.subject = subject
        self.to_list = to_list
        self.bcc_list = bcc_list or []
        self.replyto_list = replyto_list or []
        self.host = settings.BASE_DOMAIN
        self.headers = {}

        if settings.DEBUG:
            self.subject = f"[TEST] {subject}"
            self.host = "http://localhost:8080"
        elif settings.EMAIL_SUBJECT_PREFIX:
            self.subject = f"{settings.EMAIL_SUBJECT_PREFIX} {subject}"

        self.ctx["host_name"] = self.host

    def send_email(self):
        html_text = render_to_string(self.template, self.ctx)
        plain_text = strip_tags(html_text)

        MAX_RECIPIENTS = 50
        messages = []

        # Because of only 50 recipients per mail are supported in to_list or in bcc_list
        # when we have more than 50 recipients we split them in multiple parts.

        # This is done through this [i : i + MAX_RECIPIENTS] operation.
        # For example if we have 70 recipients the first time it takes from the list the
        # elements in the range [0:50] while the second time it takes elements
        # in range [50:100].
        for i in range(0, len(self.to_list), MAX_RECIPIENTS):
            msg = EmailMultiAlternatives(
                subject=self.subject,
                # The i increases by 50 at each loop, in this way we are sure to take
                # all the recipients if we have more than 50 recipients.
                to=self.to_list[i : i + MAX_RECIPIENTS],
                bcc=[],
                reply_to=self.replyto_list,
                body=plain_text,
                headers=self.headers,
            )
            msg.attach_alternative(html_text, "text/html")
            messages.append(msg)

        for i in range(0, len(self.bcc_list), MAX_RECIPIENTS):
            msg = EmailMultiAlternatives(
                subject=self.subject,
                to=[],
                # The i increases by 50 at each loop, in this way we are sure to take
                # all the recipients if we have more than 50 recipients.
                bcc=self.bcc_list[i : i + MAX_RECIPIENTS],
                reply_to=self.replyto_list,
                body=plain_text,
                headers=self.headers,
            )
            msg.attach_alternative(html_text, "text/html")
            messages.append(msg)

        for message in messages:
            try:
                logger.info("sending email...." + self.subject)
                message.send()
            except Exception as e:
                logger.exception("Error sending email: %s", e)
