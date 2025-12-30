from django.core.management.base import BaseCommand
from django.db import transaction
from frontend_content.models import FrontendContent

faq_markdown_content = """
### Definitions & Terminologies
----------

**What is Survey Designer?**

###### Survey Designer is an application that allows users in the field to build surveys in a fast and easy way while giving them the flexibility to make necessary adjustments while also maintaining WFP standard labeling & naming conventions (based on the WFP Codebook/standard list of questions and answers). This is to improve the overall data quality when it comes to survey design, data collection & analysis (saving time and resources) as well as allowing for reproducibility and sharing resources between users. This tool is targeted for users that are using XLSForm or ODK-based tools (such as: MoDa or Kobo).

**What is the Codebook?**

###### The WFP [Codebook](/admin/) is a dataset containing all possible standard questions and answers included in WFP surveys. It is linked to an XLSForm database that can be subject to integrations and revisions based on data collection needs. Questions are organized into [Modules](/admin/modules/module/) and [Submodules](/admin/modules/submodule/). The [Codebook](/admin/) in the Survey Designer cannot be directly modified, but there exists a[Request Change Procedure](/admin/change-requests/submit/) that allows you to propose your modifications to the administrators.

**What are Survey Categories, Types, Modes and Context?**

###### They are filters that you can use to structure or define your survey. Based on your choices, different submodules of questions are included in your survey. [Survey Categories](/admin/surveys/surveycategory/) are general macro-categories (currently: Monitoring, Market and Vulnerability Assessments) that define your survey. [Survey Types](/admin/surveys/surveytype/) are sub-categories specific to each category you select (e.g.: for Monitoring you have PDM, Baseline Monitoring… etc.). [Survey Modes](/admin/surveys/surveymode/) are the three data collection modes allowed for WFP surveys, namely Face-to-face, Remote/CATI and Web Surveys. Finally, [Context](/admin/surveys/surveyattribute/) are additional sets of questions that can be optionally added to specific modules (for example, COVID-19-related questions or migration-related questions).

**What are Modules and Submodules?**

###### [Modules](/admin/modules/module/) and [Submodules](/admin/modules/submodule/) (sometimes also referred as sections) are a way to group questions based on thematic areas (eg: Nutrition, Food Security… etc.) and/or on how they are normally grouped in surveys. They are organized and labelled based on standard WPF Codebook’s convention.[Submodules](/admin/modules/submodule/) are the basic unit that you will use to create a survey in Survey Designer.



###### **What are Suffixes and Recall Periods?** In the Codebook, for every question there exists several variations that are considered optional. For every question, we identify a Root Question, which expresses the basic/corporate formulation of a question. To every Root Question, we may attach different [Suffixes](/admin/questions/suffix/) and [Recall Periods](/admin/questions/recallperiod/) that indicate the variations of the Root Question. [Suffixes](/admin/questions/suffix/) indicate logic variations of the Root Question (e.g.: Root Question **HHExpFood** is to be read “What is your total food expenditure?”. If we add the suffix **_Loc** (which is related to locations), we obtain the Subquestion **HHExpFood_Loc** to be read "Where do you purchase your food?”. The Codebook allows up to a maximum of two suffixes for a single subquestion. In this case, we call the second suffix a ‘nested suffix’. [Recall Periods](/admin/questions/recallperiod/) indicate the time reference for a questions (e.g.: If we add the recall period **_7D**, indicating a weekly time reference, we obtain the Subquestion **HHExpFood_7D** to be read “What was your total food expenditure in the last 7 days?”. [Suffixes](/admin/questions/suffix/) and [Recall Periods] (/admin/questions/recallperiod/) can also be combined to create Subquestions that are both logic and temporal variations of the Root Question (e.g.: **HHExpFood_Loc_7D** should be read “Where did you purchase your food in the last 7 days?”).

**What are Calculations and Repeat Sections?**

###### [Calculations](/admin/questions/calculation/) and [Repeat Sections](/admin/questions/repeatsection/) are elements that will structure your survey but would not necessarily appear in the survey. [Calculations](/admin/questions/calculation/) are elements that produce standard calculations (aggregation, indicators scores…etc.) based on collected data. Those calculations might appear in the survey or not, based on your decision. [Repeat Sections](/admin/questions/repeatsection/)  are sections that define how a set of questions are repeated in the survey based on specific information (e.g.: asking about the age and sex of each household member, based on the household size).

### Building Surveys via Survey Designer
----------

**How do I build a survey using Survey Designer?**

###### We have a tailored step-by-step guide here and online recording here. Please check them out to know more about the process. If you have more questions, please email us at: [global.surveydesigner@wfp.org](mailto:global.surveydesigner@wfp.org)

**What kind of surveys can I build using Survey Designer?**

###### Survey Designer allows you to build any standard WFP survey that has been integrated into the Codebook. You may view the available standard WFP surveys by viewing the [Survey Categories](/admin/surveys/surveycategory/) & [Types]("/admin/surveys/surveytype/"). However, if you would like to access all available WFP questions and answers you may do so by not selecting any specific Category, Type, Mode and Attribute you can create any type of non-standard survey by combining all the modules and submodules that you need. If some of the modules/submodules from your business unit needs are not included in the Codebook, please email us at   [global.surveydesigner@wfp.org](mailto:global.surveydesigner@wfp.org) and we will guide you through the Addition Request process.

**What are the options for exporting or publishing surveys?**

###### Currently, Survey Designer allows you to export your survey as an XLSForm, or directly publish it into [MoDa](https://moda.wfp.org/) or [Kobo](https://kobo.humanitarianresponse.info/). In order to publish into [MoDa](https://moda.wfp.org/) or [Kobo](https://kobo.humanitarianresponse.info/) you would need to enter your API key (for each site) [here](/api-keys).

**Is there a limit to the modules or questions that I can select?**

###### No, you can add as many modules or questions as you need in a survey.

### Accessing & Contributing to the Codebook
----------

**How can I access the Codebook?**

###### You can access the [Codebook](/admin/) by clicking on the ‘[Codebook](/admin/)’ button on the top right next to your username. From there you should be able to access all the back-end content that contributes to building the surveys (Questions, Answers, Suffixes, Calculations, Survey Categories, Types, Modes…and others).   ![Codebook Screenshot](/static/img/codebook_screenshot.png "Codebook Screenshot")

**Can I export the Codebook content as Excel format?**

###### Yes you can do that by selecting one or more [Modules](/admin/modules/module/), [Submodules](/admin/modules/submodule/) or [Questions](/admin/questions/basequestion/) and clicking the ‘Export Questions’ action button. ![Export Action Screenshot](/static/img/export_action_screenshot.png "Export Action Screenshot")

**How can I contribute to the Codebook (request addition or changes)?**

###### You can submit requests to add, edit and/or delete any list of questions or answers (choices) to the Codebook by accessing this link [here](/admin/change-requests/submit/). Alternatively, you may send your request to: [global.surveydesigner@wfp.org](mailto:global.surveydesigner@wfp.org) by attaching an excel sheet with the required changes (please use [this template](static/change_request_template.xlsx).

### Contact Survey Designer Team
----------

###### If you have any queries or you would like to report any bugs, please send an email to: [global.surveydesigner@wfp.org](mailto:global.surveydesigner@wfp.org)
"""


tooltip_markdown_content = {
    "step1Tooltip": (
        """In this section you can select question Modules and Submodules in your
survey based on standard survey formats. Please select your Survey
Category, Type and Mode, after which you can select one or more additional
Context elements to add further contextual questions. If you would like to
access all available question modules and submodules in the system, please
do not select any option in the filters and click ‘Next’."""
    ),
    "step3Tooltip": (
        """In this section you can add additional questions based on the Modules &
Submodules that you’ve selected in the previous step. The Modules by
default include root questions (based on corporate requirements), however
you may choose to additional questions for each root question to collect
more contextual information. These additional questions are based on
Suffixes and/or Recall Periods. For more information on Suffixes and
Recall Periods, please go to the [Help Page](/help))."""
    ),
    "orgTooltip": "Please select one of the organizations below.",
    "surveyCategoryTooltip": "Please select one of the main survey categories below.",
    "surveyTypeToolTip": "Please select a survey type. Survey types are associated with survey categories, so please make sure to have selected the right survey category.",
    "surveyModeToolTip": "Please select one of the three possible survey modes.",
    "contextToolTip": "Please select all the Context elements you need. Context elements help adapt a survey to specific context or needs.",
}


class Command(BaseCommand):
    """
    Initialize the FAQ and Tooltip markdown
    """

    @transaction.atomic
    def _generate_markdown(self):
        if FrontendContent.objects.exists():
            self.stdout.write(
                self.style.SUCCESS("Frontend Content markdown already exists.")
            )
            return
        tooltip_objects = [
            FrontendContent(message=message, key=key)
            for key, message in tooltip_markdown_content.items()
        ]
        FrontendContent.objects.bulk_create(tooltip_objects)
        FrontendContent.objects.create(message=faq_markdown_content, key="FAQmain")
        self.stdout.write(
            self.style.SUCCESS(
                f"FAQ and {len(tooltip_objects)} tooltip markdown labels generated"
            )
        )

    def handle(self, *args, **options):
        self._generate_markdown()
