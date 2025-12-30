from django.core.management.base import BaseCommand
from modules.models import Module, Submodule


class Command(BaseCommand):
    """
    Fix module ordering, for deployments that already had
    """

    def _fix_module_ordering(self):
        module_orders = Module.objects.values_list("order", flat=True)
        submodule_orders = Submodule.objects.values_list("order", flat=True)

        module_obj = []

        if len(module_orders) != len(set(module_orders)):
            module_obj.append(Module)
        if len(submodule_orders) != len(set(submodule_orders)):
            module_obj.append(Submodule)

        if not len(module_obj):
            self.stdout.write(self.style.SUCCESS("Module ordering okay."))

        for module_type in module_obj:
            self.stdout.write(self.style.WARNING(f"Fixing ordering for {module_type}."))
            for i, mod in enumerate(module_type.objects.all(), 1):
                mod.order = i
                mod.save()

    def handle(self, *args, **options):
        self._fix_module_ordering()
