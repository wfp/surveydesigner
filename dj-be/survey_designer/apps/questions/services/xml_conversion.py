import inspect

from pyxform import xls2xform


class XMLConversion:
    def __init__(self, xls_file):
        self.xls_file = xls_file
        self.warnings = []
        self.errors = []

    def filter_warnings(self):
        self.warnings = [
            w for w in self.warnings if "'disabled' column header" not in w
        ]

    def run(self):
        try:
            kwargs = {
                "warnings": self.warnings,
                "validate": False,
                "pretty_print": True,
            }
            # pyxform 4.5.0 has no enketo parameter because its conversion
            # path never invokes Enketo.  Keep the explicit flag for older or
            # adapter implementations that expose it, while remaining
            # compatible with the pinned 4.5.0 API.
            parameters = inspect.signature(xls2xform.convert).parameters
            if "enketo" in parameters or any(
                parameter.kind is inspect.Parameter.VAR_KEYWORD
                for parameter in parameters.values()
            ):
                kwargs["enketo"] = False
            converted = xls2xform.convert(self.xls_file, **kwargs)
            xml = converted.xform
            self.filter_warnings()

        except Exception as e:
            self.filter_warnings()
            self.errors.append(str(e))
            return
        else:
            return xml
