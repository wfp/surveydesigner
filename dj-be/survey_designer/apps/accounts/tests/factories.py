import factory
from accounts.models import User, UserAPIKey, UserAPISite

from survey_designer.apps.accounts.const import UserAPISiteAPITypes


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User


class UserAPISiteFactory(factory.django.DjangoModelFactory):
    name = factory.Faker("name")
    api_type = factory.Sequence(lambda n: UserAPISiteAPITypes.choices[n % 2][0])
    url = factory.Faker("url")

    class Meta:
        model = UserAPISite


class UserAPIKeyFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    site = factory.SubFactory(UserAPISiteFactory)
    key = factory.Faker("password")

    class Meta:
        model = UserAPIKey
