import React, { useState, useRef, useEffect } from "react";
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
  const currentLabel = languages.find((l) => l.value === current)?.label ?? current.toUpperCase();
  const CurrentFlag = langFlags[current];

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.35rem",
          padding: "0.4rem 0.75rem",
          fontSize: "0.9375rem",
          fontWeight: 500,
          color: "#333",
          background: "transparent",
          border: "1px solid rgba(0,0,0,0.15)",
          borderRadius: "6px",
          cursor: "pointer",
        }}
        aria-expanded={open}
        aria-haspopup="listbox"
      >
        {CurrentFlag ? React.createElement(CurrentFlag) : null}
        {currentLabel}
        <span style={{ fontSize: "0.65rem", opacity: 0.8 }}>▼</span>
      </button>
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
            border: "1px solid rgba(0,0,0,0.1)",
            borderRadius: "8px",
            boxShadow: "0 4px 12px rgba(0,0,0,0.12)",
            zIndex: 1000,
          }}
        >
          {languages.map((language) => {
            const Flag = langFlags[language.value];
            return (
              <li key={language.value} role="option">
                <button
                  type="button"
                  onClick={() => {
                    onChangeLanguage(language);
                    setOpen(false);
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    width: "100%",
                    padding: "0.5rem 1rem",
                    fontSize: "0.9375rem",
                    textAlign: "left",
                    background: language.value === current ? "rgba(0,82,136,0.08)" : "transparent",
                    border: "none",
                    cursor: "pointer",
                    color: "#333",
                  }}
                >
                  {Flag ? React.createElement(Flag) : null}
                  {language.label}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
