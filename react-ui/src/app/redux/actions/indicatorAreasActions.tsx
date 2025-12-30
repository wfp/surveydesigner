import { API } from "../../utils";
import { createAppAsyncThunk } from "../store";
import { indicatorAreasActions } from "../reducers/indicatorAreasReducer";
import { indicatorsActions } from "../reducers/indicatorsReducer";
import { Indicator } from "../../types/api";
import { IndicatorAreaWithIndicators } from "../../types";

export const fetchIndicatorAreas = createAppAsyncThunk(
  "indicatorAreas/FETCH_INDICATOR_AREAS",
  async (_, { dispatch, getState }) => {
    const { surveyForm } = getState();

    const params = {
      type: surveyForm.type ? surveyForm.type.id : null,
      mode: surveyForm.mode ? surveyForm.mode.id : null,
      attributes: (surveyForm.attributes ?? []).join(","), // safer if null
    };

    try {
      const res = await API.get<Indicator[]>("/indicators/", { params });

      const OTHER_KEY = "__OTHER__";
      const areaById: Record<string, IndicatorAreaWithIndicators> = {};

      for (const obj of res.data) {
        if (!obj.indicator_area) {
          // create "Other" only when needed
          if (!areaById[OTHER_KEY]) {
            areaById[OTHER_KEY] = {
              id: 0,
              description: undefined,
              indicators: [],
              label: "Other",
              name: "Other",
              url: undefined,
              order: 9999,
            };
          }
          areaById[OTHER_KEY].indicators.push(obj);
          continue;
        }

        const key = String(obj.indicator_area.id);
        if (!areaById[key]) {
          areaById[key] = {
            id: obj.indicator_area.id,
            description: obj.indicator_area.description,
            indicators: [],
            label: obj.indicator_area.label,
            name: obj.indicator_area.name,
            url: obj.indicator_area.url,
            order: obj.indicator_area.order,
          };
        }
        areaById[key].indicators.push(obj);
      }

      const orderedAreaByIdList = Object.values(areaById)
        .filter((area) => area.indicators.length > 0) // drop empty "Other"
        .sort(
          (a, b) =>
            (a.order ?? Number.MAX_SAFE_INTEGER) -
            (b.order ?? Number.MAX_SAFE_INTEGER),
        );

      dispatch(indicatorAreasActions.setIndicatorAreas(orderedAreaByIdList));
      dispatch(indicatorsActions.setIndicators(res.data));
    } catch (err) {
      dispatch(indicatorAreasActions.setIndicatorAreasError(err));
      dispatch(indicatorsActions.setIndicatorsError(err));
    }
  },
);
