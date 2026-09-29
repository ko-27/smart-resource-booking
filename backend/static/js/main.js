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
/* =========================================================
   BOOKING ACTION CONFIRMATIONS
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const actionLinks = document.querySelectorAll(
        'a[href*="/bookings/cancel/"], ' +
        'a[href*="/bookings/approve/"], ' +
        'a[href*="/bookings/reject/"]'
    );

    actionLinks.forEach(function (link) {

        link.addEventListener("click", function (event) {

            const href = link.getAttribute("href");

            let message = "";

            if (href.includes("/bookings/cancel/")) {

                message =
                    "Are you sure you want to cancel this booking?";

            } else if (href.includes("/bookings/approve/")) {

                message =
                    "Are you sure you want to approve this booking request?";

            } else if (href.includes("/bookings/reject/")) {

                message =
                    "Are you sure you want to reject this booking request?";

            }

            if (message && !window.confirm(message)) {
                event.preventDefault();
            }

        });

    });

});

/* =========================================================
   RESOURCE ACTION CONFIRMATIONS
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const resourceActions = document.querySelectorAll(
        'a[href*="/resources/deactivate/"], ' +
        'a[href*="/resources/activate/"], ' +
        'a[href*="/resources/delete/"]'
    );

    resourceActions.forEach(function (link) {

        link.addEventListener("click", function (event) {

            const href = link.getAttribute("href");
            let message = "";

            if (href.includes("/resources/deactivate/")) {

                message =
                    "Are you sure you want to deactivate this resource?";

            } else if (href.includes("/resources/activate/")) {

                message =
                    "Are you sure you want to activate this resource?";

            } else if (href.includes("/resources/delete/")) {

                message =
                    "Are you sure you want to delete this resource? This action may not be reversible.";

            }

            if (message && !window.confirm(message)) {
                event.preventDefault();
            }

        });

    });

});
