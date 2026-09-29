/* =========================================================
   SMART RESOURCE BOOKING SYSTEM
   Main JavaScript
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    // Automatically hide flash messages after a few seconds
    const flashMessages = document.querySelectorAll(".flash");

    flashMessages.forEach(function (message) {
        setTimeout(function () {
            message.style.opacity = "0";

            setTimeout(function () {
                message.remove();
            }, 400);

        }, 4000);
    });

    // Confirmation for dangerous actions
    const dangerButtons = document.querySelectorAll(
        ".confirm-action"
    );

    dangerButtons.forEach(function (button) {
        button.addEventListener("click", function (event) {

            const message =
                button.dataset.confirm ||
                "Are you sure you want to continue?";

            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });

});