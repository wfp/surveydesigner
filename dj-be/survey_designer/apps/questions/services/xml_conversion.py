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
                "enketo": False,
            }
            converted = xls2xform.convert(self.xls_file, **kwargs)
            xml = converted.xform
            self.filter_warnings()

        except Exception as e:
            self.filter_warnings()
            self.errors.append(str(e))
            return
        else:
            return xml
