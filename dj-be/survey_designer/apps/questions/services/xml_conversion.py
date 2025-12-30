from pyxform import builder, xls2json


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
            json_survey = xls2json.parse_file_to_json(
                "preview.xlsx", warnings=self.warnings, file_object=self.xls_file
            )
            survey = builder.create_survey_element_from_dict(json_survey)

            xml = survey.to_xml(
                validate=False,
                pretty_print=True,
                warnings=self.warnings,
                enketo=False,
            )
            self.filter_warnings()

        except Exception as e:
            self.filter_warnings()
            self.errors.append(str(e))
            return
        else:
            return xml
