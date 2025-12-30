from django.db import models


## Should match question types here https://xlsform.org/en/#question-types
class QuestionType(models.TextChoices):
    AGGREGATE = "Aggregate", "Aggregate"
    CALCULATE = "calculate", "calculate"
    DECIMAL = "decimal", "decimal"
    GEOPOINT = "geopoint", "geopoint"
    GEOTRACE = "geotrace", "geotrace"
    GEOSHAPE = "geoshape", "geoshape"
    DATE = "date", "date"
    TIME = "time", "time"
    DATETIME = "dateTime", "dateTime"
    INTEGER = "integer", "integer"
    NOTE = "note", "note"
    SAME = "same", "same"
    SELECT_MULTIPLE = "select_multiple", "select_multiple"
    SELECT_ONE = "select_one", "select_one"
    SELECT_ONE_FROM_FILE = "select_one_from_file", "select_one_from_file"
    SELECT_MULTIPLE_FROM_FILE = "select_multiple_from_file", "select_multiple_from_file"
    RANK = "rank", "rank"
    ##  Not spec but defaults to text
    # STRING = "string", "string"
    TEXT = "text", "text"
    IMAGE = "image", "image"
    AUDIO = "audio", "audio"
    BACKGROUND_AUDIO = "background-audio", "background-audio"
    VIDEO = "video", "video"
    BARCODE = "barcode", "barcode"
    ACKNOWLEDGE = "acknowledge", "acknowledge"
    HIDDEN = "hidden", "hidden"
    ## TODO: documentation not clear
    # XML_EXTERNAL = "xml-external", "xml-external"

    @classmethod
    def extended_choices(cls):
        return cls.choices + [("repeat", "repeat")]


class OperatorType(models.TextChoices):
    EQUAL = "=", "="
    GREATER_THAN = ">", ">"
    GREATER_THAN_OR_EQUAL_TO = ">=", ">="
    LESS_THAN = "<", "<"
    LESS_THAN_OR_EQUAL_TO = "<=", "<="


class LogicalOperatorType(models.TextChoices):
    __empty__ = ""
    AND = "and", "and"
    OR = "or", "or"


class ReferenceQuestionType(models.TextChoices):
    SELF = "SELF", "Self"
    OTHER = "OTHER", "Other"
