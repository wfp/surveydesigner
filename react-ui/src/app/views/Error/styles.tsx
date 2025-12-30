import styled, { keyframes } from "styled-components";
import { EmergencyResponsePositive } from "@wfp/humanitarian-icons-react";

const rotateIcon = keyframes`
  from { transform: rotate(-20deg);}
  to { transform: rotate(20deg);}
`;

export const RotateIcon = styled(EmergencyResponsePositive)`
  animation: ${rotateIcon} 2s ease-in-out infinite alternate;
  fill: #0a6eb4;
  width: 200px;
  height: 200px;
  margin-bottom: 3rem;
`;
