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
  image: string;
};

export const LANDING_FEATURES: LandingFeatureItem[] = [
  {
    icon: faClipboardList,
    titleKey: "landingPage.feature1Title",
    textKey: "landingPage.feature1Text",
    image: "home_page_screen.png",
  },
  {
    icon: faGlobe,
    titleKey: "landingPage.feature2Title",
    textKey: "landingPage.feature2Text",
    image: "export_action_screenshot.png",
  },
  {
    icon: faUsers,
    titleKey: "landingPage.feature3Title",
    textKey: "landingPage.feature3Text",
    image: "home_page_screen.png",
  },
  {
    icon: faShieldAlt,
    titleKey: "landingPage.feature4Title",
    textKey: "landingPage.feature4Text",
    image: "codebook_screenshot.png",
  },
  {
    icon: faDiagramProject,
    titleKey: "landingPage.feature5Title",
    textKey: "landingPage.feature5Text",
    image: "export_action_screenshot.png",
  },
  {
    icon: faFileLines,
    titleKey: "landingPage.feature6Title",
    textKey: "landingPage.feature6Text",
    image: "codebook_screenshot.png",
  },
];
