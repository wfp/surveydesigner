import django_rq
from accounts.const import PermissionGroups
from accounts.models import User
from change_requests.const import StatusType
from change_requests.forms import ApproveChangeRequestForm, ChangeRequestForm
from change_requests.models import ChangeRequest
from core.send_email import EmailHelper
from core.tasks import send_email
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.views.generic import CreateView, UpdateView
from questions.services import DataImport


class SubmitChangeRequestView(UserPassesTestMixin, LoginRequiredMixin, CreateView):
    template_name = "change_requests/submit_change_request.html"
    form_class = ChangeRequestForm
    model = ChangeRequest

    def test_func(self):
        return self.request.user.is_authenticated

    def get_success_url(self):
        return reverse("admin:change_requests_changerequest_changelist")

    def form_valid(self, form):
        organizations = form.cleaned_data["organizations"]
        self.object = form.save(commit=False)  # create object without id
        self.object.created_by = self.request.user
        self.object.save()
        self.object = form.save_m2m()

        self.notify_change_request_group(self.object, organizations)
        return super().form_valid(form)

    def notify_change_request_group(self, obj, organizations):
        super_users_q = Q(is_superuser=True)
        global_admins_q = Q(groups__name=PermissionGroups.GLOBAL_ADMINS)

        change_request_users = User.objects.filter(
            groups__name=PermissionGroups.CHANGE_REQUESTS
        )

        if organizations.count() != 1:
            users_to_notify = change_request_users.filter(
                super_users_q | global_admins_q
            )
        else:
            users_to_notify = change_request_users.filter(
                organization=organizations.first()
            )

        if not users_to_notify:
            return

        to_list = users_to_notify.values_list("email", flat=True)

        email_queue = django_rq.get_queue("send-email")  # get the queue to send emails
        mail = EmailHelper(
            "email/new_change_request_notification.html",
            {"change_request": obj},
            subject="New Change Request.",
            to_list=to_list,
        )
        email_queue.enqueue(send_email, email_helper=mail)

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        context_data = super().get_context_data(form=form)

        if form.is_valid():
            file = form.cleaned_data["file"]

            data_import = DataImport(
                file,
                request.user,
                form.cleaned_data["organizations"],
            )
            data_import.process()

            if data_import.is_valid():
                return self.form_valid(form)
            context_data["other_errors"] = data_import.get_errors()

        return self.render_to_response(self.get_context_data(**context_data))


class ApproveChangeRequestView(UserPassesTestMixin, LoginRequiredMixin, UpdateView):
    template_name = "change_requests/process_change_request.html"
    form_class = ApproveChangeRequestForm
    model = ChangeRequest

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user_can_approve"] = self.get_object().user_can_approve(
            self.request.user
        )
        return context

    def test_func(self):
        return self.request.user.can_manage_change_requests

    def get_success_url(self):
        return reverse("admin:change_requests_changerequest_changelist")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context_data = self.get_context_data()

        with transaction.atomic():
            data_import = DataImport(
                self.object.file.file,
                request.user,
                self.object.organizations.all(),
                change_request=self.object,
            )
            data_import.process()
            data_import.create(skip_saving=True)

            context_data["other_errors"] = data_import.get_errors()
            context_data["updates"] = data_import.get_updates()
            transaction.set_rollback(True)  # making sure nothing is saved
            return self.render_to_response(context_data)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        context_data = super().get_context_data(form=form)

        if form.is_valid():
            response = form.cleaned_data.get("response", "")

            with transaction.atomic():
                data_import = DataImport(
                    self.object.file.file,
                    request.user,
                    self.object.organizations.all(),
                    change_request=self.object,
                )
                data_import.process()

                if data_import.is_valid():
                    (
                        created,
                        created_choices,
                        created_suffixes,
                        created_recall_periods,
                        created_groups,
                        created_indicators,
                    ) = data_import.create()
                    self.object.response = response
                    self.object.status = StatusType.APPROVED
                    self.object.updated_by = request.user
                    self.object.save()

                    messages.success(request, f"{self.object} successfully approved.")
                    messages.success(request, f"Questions created: {created}")

                    if data_import.existing_questions:
                        messages.success(
                            request,
                            f"Questions already in database: {', '.join(data_import.existing_questions)}",
                        )

                    return HttpResponseRedirect(self.get_success_url())

                context_data["other_errors"] = data_import.get_errors()
                context_data["updates"] = data_import.get_updates()

        return self.render_to_response(context_data)
