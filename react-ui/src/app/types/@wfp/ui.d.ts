import * as ui from "@wfp/ui";
import {
  ChangeEvent,
  ChangeEventHandler,
  ReactElement,
  ReactNode,
} from "react";

// NOTE: Temporary workarounds for incorrect TS typings in @wfp/ui package, using declaration merging
declare module "@wfp/ui" {
  export declare namespace Checkbox {
    interface CheckboxProps {
      onChange: (
        event: ChangeEvent<HTMLInputElement>,
        checked: boolean,
        customId: string
      ) => void;
    }
  }

  export declare namespace StepNavigationItem {
    interface StepNavigationItemProps {
      selectedPage?: number;
    }
  }

  export declare namespace Tooltip {
    interface TooltipProps {
      interactive?: boolean;
      delayHide?: number;
      useWrapper?: boolean;
    }
  }

  export declare namespace Icon {
    interface IconProps {
      description?: string;
    }
  }

  export declare namespace ListItem {
    interface ListItemProps {
      title?: ReactNode;
    }
  }

  export declare namespace Button {
    interface ButtonProps {
      target?: string;
    }
  }

  export declare namespace Footer {
    interface FooterProps {
      mobilePageWidth?: ui.FooterProps["pageWidth"];
      secondary?: ReactElement;
    }
  }

  export default ui;
}
