import React from "react";
import "@testing-library/jest-dom";
import "../../../locales/i18n";
import { render, screen } from "../../utils/tests";
import FaqContent from "./FaqContent";

describe("FaqContent", () => {
  it("renders translated FAQ copy with links and images", () => {
    render(<FaqContent />);

    expect(
      screen.getByRole("heading", { name: "Definitions & Terminologies" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "What is the Codebook?" }),
    ).toBeInTheDocument();

    const codebookLinks = screen.getAllByRole("link", { name: "Codebook" });
    expect(codebookLinks[0]).toHaveAttribute("href", "/admin/");
    expect(screen.getByAltText("Codebook Screenshot")).toBeInTheDocument();
    const supportLinks = screen.getAllByRole("link", {
      name: "global.surveydesigner@wfp.org",
    });
    expect(supportLinks[0]).toHaveAttribute(
      "href",
      "mailto:global.surveydesigner@wfp.org",
    );
  });
});
