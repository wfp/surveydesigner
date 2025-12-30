import factory
from django.contrib.auth import get_user_model


class AdminFactory(factory.django.DjangoModelFactory):
    password = "admin_user"
    is_staff = True

    class Meta:
        model = get_user_model()
