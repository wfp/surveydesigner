import React, { memo } from "react";
import { Empty, Button, Story, Wrapper } from "@wfp/react";

import { RotateIcon } from "./styles";

function NotFound() {
  return (
    <div>
      <Wrapper pageWidth="lg" spacing="md">
        <Story className="wfp--story__center wfp--story__full-height">
          <Empty
            kind="large"
            icon={<RotateIcon />}
            button={<Button href="/">home</Button>}
          >
            <h2 className="wfp--story__title">
              Sorry, the page you’re looking for doesn’t exist or may have been
              moved.
            </h2>
          </Empty>
        </Story>
      </Wrapper>
    </div>
  );
}

export default memo(NotFound);
