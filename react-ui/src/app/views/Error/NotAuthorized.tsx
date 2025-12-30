import React, { memo } from "react";

import { Wrapper, Story } from "@wfp/react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTriangleExclamation } from "@fortawesome/free-solid-svg-icons";

import { Link } from "react-router-dom";

function NotAuthorized() {
  return (
    <Wrapper pageWidth="lg" spacing="md">
      <Story className="wfp--story__center wfp--story__full-height">
        <FontAwesomeIcon
          icon={faTriangleExclamation}
          fill="#0a6eb4"
          width="200"
          height="200"
          style={{
            marginBottom: "3rem",
          }}
        />
        ;<h1 className="wfp--story__title">Not authorized</h1>
        <p>
          Sorry, you are not authorized to access this page.
          <br />
          <p>
            Go back <Link to="/">home</Link>
          </p>
        </p>
      </Story>
    </Wrapper>
  );
}

export default memo(NotAuthorized);
