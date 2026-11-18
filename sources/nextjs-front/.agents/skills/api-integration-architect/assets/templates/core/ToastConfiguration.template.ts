// si-archivo frontend.notificaciones=react-toastify
import { Bounce } from "react-toastify";

interface TOASTCONFIGURATIONTYPE {
  position?:
    | "bottom-right"
    | "top-right"
    | "top-center"
    | "top-left"
    | "bottom-center"
    | "bottom-left";
  autoClose?: number | false;
  hideProgressBar?: boolean;
  closeOnClick?: boolean;
  pauseOnHover?: boolean;
  draggable?: boolean | "mouse" | "touch";
  progress?: number;
  theme?: "light" | "dark" | "colored";
  transition?: typeof Bounce;
}
const DEFAULT_TOAST_CONFIG: TOASTCONFIGURATIONTYPE = {
  position: "bottom-right",
  autoClose: 5000,
  hideProgressBar: false,
  closeOnClick: false,
  pauseOnHover: true,
  draggable: true,
  progress: undefined,
  transition: Bounce,
};
export const SUCCESS_TOAST_CONFIG: TOASTCONFIGURATIONTYPE = {
  ...DEFAULT_TOAST_CONFIG,
  theme: "light",
};
export const WARNING_TOAST_CONFIG: TOASTCONFIGURATIONTYPE = {
  ...DEFAULT_TOAST_CONFIG,
  theme: "light",
};

export const ERROR_TOAST_CONFIG: TOASTCONFIGURATIONTYPE = {
  ...DEFAULT_TOAST_CONFIG,
  theme: "colored",
};
