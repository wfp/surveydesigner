import { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
  faClipboardList,
  faDiagramProject,
  faFileLines,
  faGlobe,
  faShieldAlt,
  faUsers,
} from "@fortawesome/free-solid-svg-icons";

export type LandingFeatureItem = {
  icon: IconDefinition;
  titleKey: string;
  textKey: string;
};

export const LANDING_FEATURES: LandingFeatureItem[] = [
  {
    icon: faClipboardList,
    titleKey: "landingPage.feature1Title",
    textKey: "landingPage.feature1Text",
  },
  {
    icon: faGlobe,
    titleKey: "landingPage.feature2Title",
    textKey: "landingPage.feature2Text",
  },
  {
    icon: faUsers,
    titleKey: "landingPage.feature3Title",
    textKey: "landingPage.feature3Text",
  },
  {
    icon: faShieldAlt,
    titleKey: "landingPage.feature4Title",
    textKey: "landingPage.feature4Text",
  },
  {
    icon: faDiagramProject,
    titleKey: "landingPage.feature5Title",
    textKey: "landingPage.feature5Text",
  },
  {
    icon: faFileLines,
    titleKey: "landingPage.feature6Title",
    textKey: "landingPage.feature6Text",
  },
];
