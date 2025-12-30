from django.core.management.base import BaseCommand
from django.db import transaction
from questions.factories import RootQuestionFactory

QUESTIONS = [
    {
        "name": "FCSStap",
        "submodules": [
            {"submodule_id": 4},
        ],
        "description": "Staples food consumption",
        "type": "integer",
        "label": "How many days over the last 7 days, did members of your household eat the following food items, prepared and/or consumed at home, and what was their source? (Use codes below, write 0 if not consumed in last 7 days). Note for enumerator: Determine whether consumption of fish, milk was only in small quantities.",
        "sub_questions": [
            {"suffix_id": 2, "label": "Source of food?"},
        ],
    },
    {
        "name": "FCSPr",
        "submodules": [
            {"submodule_id": 4},
        ],
        "description": "Protein food consumption",
        "type": "integer",
        "label": "How many days has your household consumed protein-rich foods in the past 7 days?",
    },
    {
        "name": "rCSILessQlty",
        "submodules": [
            {"submodule_id": 3},
        ],
        "description": "Rely on less preferred and less expensive food",
        "type": "integer",
        "label": "During the last 7 days, were there days (and, if so, how many) when your household had to employ one of the following strategies (to cope with a lack of food or money to buy it)?",
        "hint": "Answer between 0 and 7 days.",
        "sub_questions": [
            {
                "suffix_id": 5,
                "label": "During the last 7 days, were there days when your household had to employ one of the following strategies (to cope with a lack of food or money to buy it)?",
            },
            {"suffix_id": 1, "label": "Other, please specify"},
        ],
    },
    {
        "name": "EnuSex",
        "submodules": [
            {"submodule_id": 7},
        ],
        "description": "Sex of the Interviewer/Enumerator. Can be useful in some bias.",
        "type": "select_one",
        "choices_id": 2,
        "label": "Sex of the interviewer",
        "sub_questions": [{"suffix_id": 1, "label": "Other, please specify"}],
    },
]


class Command(BaseCommand):
    """
    Generate questions
    """

    @transaction.atomic
    def _generate_questions(self):
        for question_data in QUESTIONS:
            RootQuestionFactory.create(**question_data)

        self.stdout.write(self.style.SUCCESS("Questions generated"))

    def handle(self, *args, **options):
        self._generate_questions()
