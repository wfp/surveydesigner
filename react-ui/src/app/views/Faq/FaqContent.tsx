import React, { ReactNode } from "react";
import { Link } from "@wfp/react";
import { Trans, useTranslation } from "react-i18next";

interface FaqSectionProps {
  title: string;
  children: ReactNode;
}

function FaqSection({ title, children }: FaqSectionProps) {
  return (
    <section>
      <h3>{title}</h3>
      {children}
    </section>
  );
}

interface FaqItemProps {
  question?: string;
  children: ReactNode;
}

function FaqItem({ question, children }: FaqItemProps) {
  return (
    <article>
      {question && <h4>{question}</h4>}
      <blockquote className="wfp-blockquote">{children}</blockquote>
    </article>
  );
}

interface FaqParagraphProps {
  children: ReactNode;
}

function FaqParagraph({ children }: FaqParagraphProps) {
  return <p>{children}</p>;
}

interface FaqLinkProps {
  href: string;
  children?: ReactNode;
}

function FaqLink({ href, children }: FaqLinkProps) {
  const shouldOpenNewTab = !href.startsWith("mailto:");

  return (
    <Link
      href={href}
      {...(shouldOpenNewTab
        ? { target: "_blank", rel: "noopener noreferrer" }
        : {})}
    >
      {children}
    </Link>
  );
}

interface FaqTextProps {
  i18nKey: string;
  components?: Record<string, JSX.Element>;
}

function FaqText({ i18nKey, components }: FaqTextProps) {
  return (
    <FaqParagraph>
      <Trans components={components} i18nKey={i18nKey} />
    </FaqParagraph>
  );
}

interface FaqImageProps {
  alt: string;
  src: string;
}

function FaqImage({ alt, src }: FaqImageProps) {
  return (
    <div className="img-wrapper">
      <img alt={alt} className="responsive" loading="lazy" src={src} />
    </div>
  );
}

function FaqContent() {
  const { t } = useTranslation();

  const transComponents = {
    strong: <strong />,
    codebook: <FaqLink href="/admin/" />,
    modules: <FaqLink href="/admin/modules/module/" />,
    submodules: <FaqLink href="/admin/modules/submodule/" />,
    requestChangeProcedure: <FaqLink href="/admin/change-requests/submit/" />,
    surveyCategories: <FaqLink href="/admin/surveys/surveycategory/" />,
    surveyTypes: <FaqLink href="/admin/surveys/surveytype/" />,
    surveyModes: <FaqLink href="/admin/surveys/surveymode/" />,
    context: <FaqLink href="/admin/surveys/surveyattribute/" />,
    suffixes: <FaqLink href="/admin/questions/suffix/" />,
    recallPeriods: <FaqLink href="/admin/questions/recallperiod/" />,
    calculations: <FaqLink href="/admin/questions/calculation/" />,
    repeatSections: <FaqLink href="/admin/questions/repeatsection/" />,
    apiKeysPage: <FaqLink href="/api-keys" />,
    supportEmail: <FaqLink href="mailto:global.surveydesigner@wfp.org" />,
    moda: <FaqLink href="https://moda.wfp.org/" />,
    kobo: <FaqLink href="https://kobo.humanitarianresponse.info/" />,
    questions: <FaqLink href="/admin/questions/basequestion/" />,
    submitChangeRequest: <FaqLink href="/admin/change-requests/submit/" />,
    changeRequestTemplate: (
      <FaqLink href="/static/change_request_template.xlsx" />
    ),
  };

  return (
    <>
      <FaqSection title={t("helpPage.sections.definitions.title")}>
        <FaqItem
          question={t(
            "helpPage.sections.definitions.items.surveyDesigner.question",
          )}
        >
          <FaqText i18nKey="helpPage.sections.definitions.items.surveyDesigner.paragraph1" />
        </FaqItem>

        <FaqItem
          question={t("helpPage.sections.definitions.items.codebook.question")}
        >
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.codebook.paragraph1"
          />
          <FaqText i18nKey="helpPage.sections.definitions.items.codebook.paragraph2" />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.codebook.paragraph3"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.codebook.paragraph4"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.definitions.items.categoriesTypesModesContext.question",
          )}
        >
          <FaqText i18nKey="helpPage.sections.definitions.items.categoriesTypesModesContext.paragraph1" />
          <FaqText i18nKey="helpPage.sections.definitions.items.categoriesTypesModesContext.paragraph2" />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.categoriesTypesModesContext.paragraph3"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.categoriesTypesModesContext.paragraph4"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.categoriesTypesModesContext.paragraph5"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.categoriesTypesModesContext.paragraph6"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.definitions.items.modulesSubmodules.question",
          )}
        >
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.modulesSubmodules.paragraph1"
          />
          <FaqText i18nKey="helpPage.sections.definitions.items.modulesSubmodules.paragraph2" />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.modulesSubmodules.paragraph3"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.definitions.items.suffixesRecallPeriods.question",
          )}
        >
          <FaqText i18nKey="helpPage.sections.definitions.items.suffixesRecallPeriods.paragraph1" />
          <FaqText i18nKey="helpPage.sections.definitions.items.suffixesRecallPeriods.paragraph2" />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.suffixesRecallPeriods.paragraph3"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.suffixesRecallPeriods.paragraph4"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.suffixesRecallPeriods.paragraph5"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.definitions.items.calculationsRepeatSections.question",
          )}
        >
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.calculationsRepeatSections.paragraph1"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.calculationsRepeatSections.paragraph2"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.definitions.items.calculationsRepeatSections.paragraph3"
          />
        </FaqItem>
      </FaqSection>

      <FaqSection title={t("helpPage.sections.buildingSurveys.title")}>
        <FaqItem
          question={t(
            "helpPage.sections.buildingSurveys.items.buildSurvey.question",
          )}
        >
          <FaqText i18nKey="helpPage.sections.buildingSurveys.items.buildSurvey.paragraph1" />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.buildingSurveys.items.buildSurvey.paragraph2"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.buildingSurveys.items.surveyTypes.question",
          )}
        >
          <FaqText i18nKey="helpPage.sections.buildingSurveys.items.surveyTypes.paragraph1" />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.buildingSurveys.items.surveyTypes.paragraph2"
          />
          <FaqText i18nKey="helpPage.sections.buildingSurveys.items.surveyTypes.paragraph3" />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.buildingSurveys.items.surveyTypes.paragraph4"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.buildingSurveys.items.exportPublish.question",
          )}
        >
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.buildingSurveys.items.exportPublish.paragraph1"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.buildingSurveys.items.exportPublish.paragraph2"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.buildingSurveys.items.selectionLimit.question",
          )}
        >
          <FaqText i18nKey="helpPage.sections.buildingSurveys.items.selectionLimit.paragraph1" />
        </FaqItem>
      </FaqSection>

      <FaqSection title={t("helpPage.sections.codebookAccess.title")}>
        <FaqItem
          question={t(
            "helpPage.sections.codebookAccess.items.accessCodebook.question",
          )}
        >
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.codebookAccess.items.accessCodebook.paragraph1"
          />
          <FaqText i18nKey="helpPage.sections.codebookAccess.items.accessCodebook.paragraph2" />
          <FaqImage
            alt={t(
              "helpPage.sections.codebookAccess.items.accessCodebook.imageAlt",
            )}
            src="/img/codebook_screenshot.png"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.codebookAccess.items.exportExcel.question",
          )}
        >
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.codebookAccess.items.exportExcel.paragraph1"
          />
          <FaqImage
            alt={t(
              "helpPage.sections.codebookAccess.items.exportExcel.imageAlt",
            )}
            src="/img/export_action_screenshot.png"
          />
        </FaqItem>

        <FaqItem
          question={t(
            "helpPage.sections.codebookAccess.items.contributeChanges.question",
          )}
        >
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.codebookAccess.items.contributeChanges.paragraph1"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.codebookAccess.items.contributeChanges.paragraph2"
          />
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.codebookAccess.items.contributeChanges.paragraph3"
          />
        </FaqItem>
      </FaqSection>

      <FaqSection title={t("helpPage.sections.contact.title")}>
        <FaqItem>
          <FaqText
            components={transComponents}
            i18nKey="helpPage.sections.contact.paragraph1"
          />
        </FaqItem>
      </FaqSection>
    </>
  );
}

export default FaqContent;
