import factory
from modules.models import Module, Submodule


class ModuleFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Module {n}")

    class Meta:
        model = Module


class SubmoduleFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: f"Submodule {n}")
    module = factory.SubFactory(ModuleFactory)

    class Meta:
        model = Submodule
