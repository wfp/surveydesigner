import axios from "axios";
import { Link, Text } from "@wfp/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import React, { PropsWithChildren, ReactElement } from "react";
import { FrontendContent, SavedSurvey } from "../types/api";

/*
 * getVersion()
 * return the latest software version retrieved from the pipeline or inside package.json
 */
const getVersion = () => {
  // eslint-disable-next-line no-console
  console.log("Build ID: ", import.meta.env.VITE_BUILD_ID);
  const version = `${import.meta.env.VITE_BUILD_ID || "dev"}`;
  return version;
};

export const VERSION = getVersion();

export const API = axios.create({
  baseURL: `${import.meta.env.VITE_APP_API_ENDPOINT}/api/`,
  withCredentials: true,
});

export const getCompareFunction = <T extends { id: number }>(
  orderSource: number[],
) => {
  function compare(itemA: T, itemB: T) {
    let indexA = orderSource.indexOf(itemA.id);
    let indexB = orderSource.indexOf(itemB.id);

    indexA = indexA === -1 ? orderSource.length : indexA;
    indexB = indexB === -1 ? orderSource.length : indexB;

    return indexA - indexB;
  }
  return compare;
};

export const capitalize = ([first, ...rest]: string, lowerRest = true) =>
  first.toUpperCase() +
  (lowerRest ? rest.join("").toLowerCase() : rest.join(""));

interface LinkRendererProps extends PropsWithChildren {
  href?: string;
}

function LinkRenderer(props: LinkRendererProps) {
  // always create links in new tabs
  return (
    <Link href={props.href} target="_blank" rel="noreferrer">
      {props.children}
    </Link>
  );
}

type TextRendererProps = PropsWithChildren;

function TextRenderer(props: TextRendererProps) {
  // match style of Text for rendered markdown
  return <Text>{props.children}</Text>;
}

interface RenderMarkdownFunction {
  (data: FrontendContent[] | null, key: string): ReactElement;
}

export const renderTooltipMarkdown: RenderMarkdownFunction = (data, key) => {
  // fetch markdown from frontend-content endpoint based on key
  const content = data?.find((data) => data?.key === key)?.message;
  return (
    <Text>
      <ReactMarkdown
        components={{
          a: LinkRenderer,
          p: TextRenderer,
        }}
        remarkPlugins={[remarkGfm]}
      >
        {`${content}`}
      </ReactMarkdown>
    </Text>
  );
};

export const getSurveyTags = (selectedSavedSurvey: SavedSurvey | undefined) => {
  const tags = [];
  if (selectedSavedSurvey) {
    selectedSavedSurvey.organizations.forEach((org) => {
      tags.push(org.name);
    });
    if (selectedSavedSurvey.survey_category) {
      tags.push(selectedSavedSurvey.survey_category.label);
    }
    if (selectedSavedSurvey.survey_type) {
      tags.push(selectedSavedSurvey.survey_type.label);
    }
    if (selectedSavedSurvey.survey_mode) {
      tags.push(selectedSavedSurvey.survey_mode.label);
    }
    selectedSavedSurvey.attributes.forEach((att) => {
      tags.push(att.label);
    });
    return tags;
  }
  return [];
};
