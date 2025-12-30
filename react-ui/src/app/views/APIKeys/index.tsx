import React, { useEffect, useRef, useState } from "react";
import {
  Module,
  ModuleBody,
  TextInput,
  Button,
  FormGroup,
  Callout,
} from "@wfp/react";

import _ from "lodash";
import { Cookies } from "react-cookie";
import Select from "react-select";
import { AxiosResponse } from "axios";
import { useAppSelector } from "../../redux/store";
import MainLayout from "../../components/Layout";
import SensitiveTextInput from "../../components/SensitiveTextInput";
import { API } from "../../utils";
import {
  UserAPIKey,
  PatchedUserAPIKeyRequest,
  UserAPISite,
  UserAPIKeyRead,
} from "../../types/api";
import { ApiError } from "../../types";
import { Notification } from "./APIKeys.interface";

function ApiKeys() {
  const baseUrl = "/accounts/api-keys/";
  const auth = useAppSelector((state) => state.auth);
  const [apiSites, setApiSites] = useState<UserAPISite[]>([]);
  const [apiKeys, setApiKeys] = useState<UserAPIKey[] | null>(null);
  const [newApiKeys, setNewApiKeys] = useState<UserAPIKey[]>([]);
  const [notifications, setNotifications] = useState<Notification[]>([]);

  const config = useRef(
    (() => {
      const cookies = new Cookies();
      return {
        headers: {
          "X-CSRFToken": cookies.get("csrftoken"),
        },
      };
    })(),
  );

  const fetchApiSites = () => {
    API.get("/accounts/api-sites/")
      .then((res) => {
        setApiSites(res.data);
      })
      .catch((err) => {
        setNotifications([
          ...notifications,
          {
            kind: "error",
            title: "Error",
            subtitle: "Problem with fetching api sites.",
          },
        ]);
      });
  };

  useEffect(() => {
    if (!auth.is_logged) {
      return;
    }

    API.get<UserAPIKeyRead[]>(baseUrl)
      .then((res) => {
        const apiKeys = res.data.map((apiKey) => ({
          ...apiKey,
          site: apiKey.site?.id,
        }));

        setApiKeys(apiKeys);
        setNewApiKeys(apiKeys);
      })
      .catch((err) => {
        setNotifications([
          ...notifications,
          {
            kind: "error",
            title: "Error",
            subtitle: "Problem with fetching api keys.",
          },
        ]);
      });

    fetchApiSites();
  }, [auth.is_logged]);

  function canUpdate(index: number) {
    if (!apiKeys) return false;

    const apiKey = apiKeys[index];
    const newApiKey = newApiKeys[index];

    const initialSite = apiKey?.site;
    const initialApiKey = apiKey?.raw_key ?? "";
    const initialName = apiKey?.name ?? "";

    const didSiteChange = newApiKey.site !== initialSite;
    const didApiKeyChange = newApiKey.raw_key !== initialApiKey;
    const didNameChange = newApiKey.name !== initialName;

    return didSiteChange || didApiKeyChange || didNameChange;
  }

  function handleKeyChange(
    event: React.ChangeEvent<HTMLInputElement>,
    index: number,
  ) {
    const keys = [...newApiKeys];
    keys[index] = {
      ...keys[index],
      raw_key: event.target.value,
    };

    setNewApiKeys(keys);
  }

  function handleNameChange(
    event: React.ChangeEvent<HTMLInputElement>,
    index: number,
  ) {
    const keys = [...newApiKeys];
    keys[index] = {
      ...keys[index],
      name: event.target.value,
    };

    setNewApiKeys(keys);
  }

  function handleSiteChange(apiSite: UserAPISite | null, index: number) {
    const keys = [...newApiKeys];
    keys[index] = {
      ...keys[index],
      site: apiSite?.id,
    };

    setNewApiKeys(keys);
  }

  function addApiKey() {
    const keys = [...newApiKeys];
    keys.push({
      id: null as unknown as number, // TODO: Find better way to do it
      site: null,
      site_url: "",
      raw_key: "",
      name: "",
      is_name_required: true,
      skip_projects: false,
    });
    setNewApiKeys(keys);
  }

  function getErrorMessage(error: ApiError): string {
    const { response } = error;
    if (response && response.data) {
      if (response.data.message) {
        return response.data.message;
      }
      if (response.data.non_field_errors) {
        return response.data.non_field_errors.join(", ");
      }
    }
    return error.message;
  }

  function handleUpdate(index: number) {
    if (!apiKeys) return;

    const original = apiKeys[index];
    const edited = newApiKeys[index];
    const { site, raw_key: rawKey, name } = edited;

    if (edited.id) {
      const url = `${baseUrl}${edited.id}/`;

      const payload: PatchedUserAPIKeyRequest = {
        ...(site !== original.site ? { site } : {}),
        ...(name !== original.name ? { name } : {}),
        ...(rawKey ? { raw_key: rawKey } : {}),
      };

      if (Object.keys(payload).length === 0) return;

      API.patch<
        UserAPIKey,
        AxiosResponse<UserAPIKey>,
        PatchedUserAPIKeyRequest
      >(url, payload, config.current)
        .then((res) => {
          const apiKeysCopy = [...apiKeys];
          const newApiKeysCopy = [...newApiKeys];
          const updated = { ...res.data, raw_key: rawKey };
          apiKeysCopy[index] = updated;
          newApiKeysCopy[index] = updated;
          setApiKeys(apiKeysCopy);
          setNewApiKeys(newApiKeysCopy);

          setNotifications([
            ...notifications,
            {
              kind: "success",
              title: "Succcess",
              subtitle: "API Key has been updated.",
            },
          ]);
        })
        .catch((err) => {
          setNotifications([
            ...notifications,
            {
              kind: "error",
              title: "Error",
              subtitle: getErrorMessage(err),
            },
          ]);
        });
    } else {
      // CREATE
      API.post(
        baseUrl,
        {
          raw_key: rawKey,
          site,
          name,
        },
        config.current,
      )
        .then((res) => {
          const normalized = {
            ...res.data,
            site: (res.data as any)?.site?.id ?? res.data.site,
            raw_key: rawKey, // keep what user typed visible
          };
          const apiKeysCopy = [...(apiKeys ?? [])];
          const newApiKeysCopy = [...(newApiKeys ?? [])];
          apiKeysCopy[index] = normalized;
          newApiKeysCopy[index] = normalized;
          setApiKeys(apiKeysCopy);
          setNewApiKeys(newApiKeysCopy);
          setNotifications([
            ...notifications,
            {
              kind: "success",
              title: "Succcess",
              subtitle: "API Key has been set.",
            },
          ]);
        })
        .catch((err) => {
          setNotifications([
            ...notifications,
            {
              kind: "error",
              title: "Error",
              subtitle: getErrorMessage(err),
            },
          ]);
        });
    }
  }

  function handleDelete(index: number) {
    const id = newApiKeys[index]?.id;
    if (!id) return;

    const url = `${baseUrl}${id}/`;
    API.delete(url, config.current)
      .then(() => {
        setApiKeys((prev) => prev!.filter((k) => k.id !== id));
        setNewApiKeys((prev) => prev.filter((k) => k.id !== id));
        setNotifications([
          ...notifications,
          {
            kind: "success",
            title: "Succcess",
            subtitle: "API Key has been removed.",
          },
        ]);
      })
      .catch((err) => {
        setNotifications([
          ...notifications,
          { kind: "error", title: "Error", subtitle: getErrorMessage(err) },
        ]);
      });
  }

  const getUpdateButtonLabel = (apiKey: UserAPIKey) => {
    if (apiKey.id === null) return "Add";
    return "Update";
  };

  const renderApiKey = (apiKey: UserAPIKey, index: number) => {
    const apiSite = apiSites.find(({ id }) => id === apiKey.site);

    return (
      <FormGroup key={`${apiKey.site}-${index}`}>
        <div
          style={{
            marginBottom: "2rem",
            width: "100%",
            maxWidth: "900px",
            display: "grid",
            gridTemplateColumns: "250px 190px 1fr 90px 90px",
            gap: "1.3rem",
            alignItems: "end",
            background: "#f8f9fb",
            padding: "1rem 0.5rem",
            borderRadius: "8px",
            boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
          }}
        >
          <div
            style={{ display: "flex", flexDirection: "column", minWidth: 0 }}
          >
            <Select
              className="wfp--react-select-container"
              classNamePrefix="wfp--react-select"
              id="id_site_select"
              defaultValue={null}
              value={apiSite}
              options={apiSites}
              getOptionValue={(apiSite) => `${apiSite.id}`}
              getOptionLabel={(apiSite) => apiSite.name}
              onChange={(e) => handleSiteChange(e, index)}
            />
            {apiSite && (
              <a
                href={apiSite.url}
                target="_blank"
                rel="noopener noreferrer"
                className="wfp--form__helper-text"
                style={{
                  fontSize: "0.82em",
                  wordBreak: "break-all",
                  marginTop: 3,
                  marginLeft: 2,
                }}
              >
                {apiSite.url}
              </a>
            )}
          </div>
          <div style={{ width: "100%" }}>
            <SensitiveTextInput
              id="id_name_input"
              value={apiKey.raw_key || ""}
              placeholder="API Key"
              onChange={(e) => handleKeyChange(e, index)}
              style={{ width: "100%" }}
            />
          </div>
          <div style={{ width: "100%" }}>
            <TextInput
              value={apiKey.name || ""}
              placeholder="Unique Name (Project Name)"
              onChange={(e) => handleNameChange(e, index)}
              style={{ width: "100%" }}
            />
          </div>
          <div>
            <Button
              style={{ width: "100%" }}
              disabled={!canUpdate(index)}
              onClick={() => handleUpdate(index)}
            >
              {getUpdateButtonLabel(apiKey)}
            </Button>
          </div>
          {apiKey.id && (
            <div>
              <Button
                style={{ width: "100%" }}
                kind="danger"
                onClick={() => handleDelete(index)}
              >
                Delete
              </Button>
            </div>
          )}
        </div>
      </FormGroup>
    );
  };

  return (
    <MainLayout
      title="Manage API Keys"
      subTitle="Set up and manage your MoDa, Moda-DEV and Kobo api keys."
    >
      <div style={{ position: "fixed", bottom: 20, right: 20, zIndex: 2 }}>
        {!_.isEmpty(notifications) &&
          notifications.map((item, index) => (
            <Callout
              // eslint-disable-next-line react/no-array-index-key
              key={`${item.kind}${index}`}
              iconDescription="close"
              kind={item.kind}
              lowContrast
              statusIconDescription=""
              subtitle={item.subtitle}
              title={item.title}
              // eslint-disable-next-line jsx-a11y/aria-role
              role="notification"
              isDismissible={true}
            />
          ))}
      </div>

      <Module>
        <ModuleBody>
          {_.isEmpty(apiKeys) && <div>API Keys not available.</div>}

          <div
            className="d-flex align-items-center"
            style={{ flexDirection: "column" }}
          >
            {newApiKeys.map(renderApiKey)}
            <Button style={{ marginLeft: "2rem" }} onClick={() => addApiKey()}>
              Add API Key
            </Button>
          </div>
        </ModuleBody>
      </Module>
    </MainLayout>
  );
}

export default ApiKeys;
