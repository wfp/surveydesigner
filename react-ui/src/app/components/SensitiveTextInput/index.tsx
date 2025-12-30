import { TextInput } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faEye, faEyeSlash } from "@fortawesome/free-solid-svg-icons";
import React, { useState } from "react";

// Reuse TextInput props, except we control `type`
type SensitiveTextInputProps = Omit<
  React.ComponentProps<typeof TextInput>,
  "type"
>;

function SensitiveTextInput({
  id,
  value,
  onChange,
  placeholder,
  style,
  ...rest
}: SensitiveTextInputProps) {
  const [isVisible, setIsVisible] = useState(false);

  return (
    <div className="d-flex" style={{ width: "100%", alignItems: "flex-end" }}>
      <TextInput
        id={id}
        data-testid="textinput"
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        style={style}
        type={isVisible ? ("text" as any) : ("password" as any)}
        autoComplete="new-password"
        {...rest}
      />
      <div
        className="d-flex align-items-center"
        style={{ height: 40, marginLeft: "0.5rem" }}
      >
        <FontAwesomeIcon
          role="button"
          aria-label={isVisible ? "Hide key" : "Show key"}
          onClick={() => setIsVisible((v) => !v)}
          icon={isVisible ? faEye : faEyeSlash}
          className="wfp--btn__icon"
          style={{ cursor: "pointer", width: 15, height: 15 }}
        />
      </div>
    </div>
  );
}

export default SensitiveTextInput;
