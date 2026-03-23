import React, { useState, useRef, useEffect } from "react";
import { Button } from "@wfp/react";
import { langFlags } from "./flags";
import { languages, onChangeLanguage, getUserLanguage } from "../../utils/i18n";

export function LanguageDropdown() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const current = getUserLanguage();
  const currentLabel =
    languages.find((l) => l.value === current)?.label ?? current.toUpperCase();
  const CurrentFlag = langFlags[current];

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <Button
        kind="ghost"
        small
        icon={CurrentFlag ? React.createElement(CurrentFlag) : undefined}
        iconReverse
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        {currentLabel}
      </Button>
      {open && (
        <ul
          role="listbox"
          style={{
            position: "absolute",
            top: "100%",
            right: 0,
            marginTop: "4px",
            minWidth: "160px",
            padding: "4px 0",
            listStyle: "none",
            background: "#fff",
            border: "1px solid rgba(0, 0, 0, 0.1)",
            borderRadius: "8px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.12)",
            zIndex: 1000,
          }}
        >
          {languages.map((language) => {
            const Flag = langFlags[language.value];
            return (
              <li key={language.value} role="option">
                <Button
                  kind="ghost"
                  small
                  icon={Flag ? React.createElement(Flag) : undefined}
                  iconReverse
                  onClick={() => {
                    void onChangeLanguage(language);
                    setOpen(false);
                  }}
                  style={{
                    justifyContent: "flex-start",
                    width: "100%",
                    padding: "0.5rem 1rem",
                    background:
                      language.value === current
                        ? "rgba(0, 82, 136, 0.08)"
                        : "transparent",
                  }}
                >
                  {language.label}
                </Button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
