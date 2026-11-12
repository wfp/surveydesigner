import type { AxiosResponse } from "axios";
import { vi } from "vitest";
import { API } from ".";
import { AppDispatch } from "../redux/store";
import { generateDoc, getXLS } from "./generate";

vi.mock("./download", () => ({
  downloadFile: vi.fn(),
}));

describe("survey generation organization headers", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  const dispatch = vi.fn() as unknown as AppDispatch;
  const response = {
    data: {},
    headers: {},
  } as unknown as AxiosResponse;

  it("sends shared survey organizations for XLSX and DOCX generation", async () => {
    const post = vi
      .spyOn(API, "post")
      .mockReturnValue(Promise.resolve(response));
    const surveyForm = {
      submodules: [1],
      submodules_order: [],
      subquestion_submodule_mapping: {},
      organizations: [{ id: 1 }],
    };

    await getXLS(dispatch, surveyForm, undefined, true);
    generateDoc(dispatch, surveyForm, undefined, true);

    expect(post).toHaveBeenNthCalledWith(
      1,
      "/generate/",
      expect.anything(),
      expect.objectContaining({
        headers: expect.objectContaining({
          "Survey-Designer-Organizations": "1",
        }),
      }),
    );
    expect(post).toHaveBeenNthCalledWith(
      2,
      "/generate-doc/",
      expect.anything(),
      expect.objectContaining({
        headers: expect.objectContaining({
          "Survey-Designer-Organizations": "1",
        }),
      }),
    );
  });

  it("omits the organization header when the survey has no organizations", async () => {
    const post = vi
      .spyOn(API, "post")
      .mockReturnValue(Promise.resolve(response));
    const surveyForm = {
      submodules: [1],
      submodules_order: [],
      subquestion_submodule_mapping: {},
    };

    await getXLS(dispatch, surveyForm, undefined, true);

    expect(post).toHaveBeenCalledWith(
      "/generate/",
      expect.anything(),
      expect.objectContaining({
        headers: expect.not.objectContaining({
          "Survey-Designer-Organizations": expect.anything(),
        }),
      }),
    );
  });
});
