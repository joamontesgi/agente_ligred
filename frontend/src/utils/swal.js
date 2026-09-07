import Swal from "sweetalert2";

const baseConfig = {
  cancelButtonColor: "#5f6f68",
  buttonsStyling: true,
  customClass: {
    popup: "swal-app-popup",
    title: "swal-app-title",
    htmlContainer: "swal-app-text",
    confirmButton: "swal-app-confirm",
    cancelButton: "swal-app-cancel",
  },
};

export async function confirmAction({
  title = "¿Estás seguro?",
  text = "",
  confirmText = "Confirmar",
  cancelText = "Cancelar",
  icon = "warning",
  danger = false,
}) {
  const result = await Swal.fire({
    ...baseConfig,
    title,
    text,
    icon,
    showCancelButton: true,
    confirmButtonText: confirmText,
    cancelButtonText: cancelText,
    confirmButtonColor: danger ? "#b42318" : "#1b6b4a",
    reverseButtons: true,
    focusCancel: true,
  });

  return result.isConfirmed;
}

export function showSuccess(message, title = "Listo") {
  return Swal.fire({
    ...baseConfig,
    title,
    text: message,
    icon: "success",
    confirmButtonColor: "#1b6b4a",
    timer: 2200,
    showConfirmButton: false,
  });
}

export function showError(message, title = "Error") {
  return Swal.fire({
    ...baseConfig,
    title,
    text: message,
    icon: "error",
    confirmButtonColor: "#1b6b4a",
  });
}
