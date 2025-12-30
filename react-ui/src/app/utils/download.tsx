import { AxiosResponse } from "axios";

export function downloadFile(
  res: AxiosResponse,
  timestamp: string,
  mimetype: string,
  fileExtension: string
) {
  const url = window.URL.createObjectURL(
    new Blob([res.data], { type: mimetype })
  );

  const a = document.createElement("a");
  a.href = url;
  a.download = `survey_${timestamp}.${fileExtension}`;
  a.click();
}
