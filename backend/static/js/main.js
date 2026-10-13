/* =========================================================
   SMART RESOURCE BOOKING SYSTEM
   Enhanced Interactions & Micro-Animations
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    // 1. Auto-dismiss flash messages with smooth fade-out and slide-up
    const flashMessages = document.querySelectorAll(".flash, .flash-message");

    flashMessages.forEach(function (message) {
        // Add dismiss cross
        const closeBtn = document.createElement("span");
        closeBtn.innerHTML = "&times;";
        closeBtn.style.cursor = "pointer";
        closeBtn.style.marginLeft = "15px";
        closeBtn.style.fontSize = "1.2rem";
        closeBtn.style.fontWeight = "bold";
        closeBtn.style.opacity = "0.7";
        closeBtn.title = "Dismiss";
        closeBtn.addEventListener("click", function () {
            message.style.opacity = "0";
            message.style.transform = "translateY(-8px)";
            setTimeout(function () {
                message.remove();
            }, 300);
        });
        message.appendChild(closeBtn);

        // Auto fade out after 5 seconds
        setTimeout(function () {
            if (message.parentNode) {
                message.style.opacity = "0";
                message.style.transform = "translateY(-8px)";
                setTimeout(function () {
                    if (message.parentNode) {
                        message.remove();
                    }
                }, 300);
            }
        }, 5000);
    });

    // 2. Prevent past dates in booking form
    const bookingDateInput = document.getElementById("booking_date");
    if (bookingDateInput) {
        const todayStr = new Date().toISOString().split("T")[0];
        bookingDateInput.setAttribute("min", todayStr);
    }

    // 3. Double-submit prevention with feedback
    const forms = document.querySelectorAll("form");
    forms.forEach(function (form) {
        form.addEventListener("submit", function (e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn && !submitBtn.disabled) {
                // Allow a brief moment so native HTML5 validation and submit trigger
                setTimeout(function () {
                    submitBtn.style.opacity = "0.75";
                    submitBtn.style.cursor = "wait";
                }, 50);
            }
        });
    });

    // 4. Booking Action Confirmations
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
                message = "Are you sure you want to cancel this booking?";
            } else if (href.includes("/bookings/approve/")) {
                message = "Are you sure you want to approve this booking request?";
            } else if (href.includes("/bookings/reject/")) {
                message = "Are you sure you want to reject this booking request?";
            }

            if (message && !window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    // 5. Resource Action Confirmations
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
                message = "Are you sure you want to deactivate this resource?";
            } else if (href.includes("/resources/activate/")) {
                message = "Are you sure you want to activate this resource?";
            } else if (href.includes("/resources/delete/")) {
                message = "Are you sure you want to delete this resource? This action may not be reversible.";
            }

            if (message && !window.confirm(message)) {
                event.preventDefault();
            }
        });
    });

    // 6. Generic confirmation for dangerous actions
    const dangerButtons = document.querySelectorAll(".confirm-action");
    dangerButtons.forEach(function (button) {
        button.addEventListener("click", function (event) {
            const message = button.dataset.confirm || "Are you sure you want to continue?";
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });

    // 7. Profile dropdown / popover toggle
    const profileBtn = document.getElementById("profileDropdownBtn");
    const profilePopover = document.getElementById("profilePopover");

    if (profileBtn && profilePopover) {
        profileBtn.addEventListener("click", function (event) {
            event.stopPropagation();
            const isOpen = profilePopover.classList.toggle("show");
            profileBtn.setAttribute("aria-expanded", isOpen ? "true" : "false");
        });

        document.addEventListener("click", function (event) {
            if (!profilePopover.contains(event.target) && !profileBtn.contains(event.target)) {
                profilePopover.classList.remove("show");
                profileBtn.setAttribute("aria-expanded", "false");
            }
        });

        document.addEventListener("keydown", function (event) {
            if (event.key === "Escape" && profilePopover.classList.contains("show")) {
                profilePopover.classList.remove("show");
                profileBtn.setAttribute("aria-expanded", "false");
                profileBtn.focus();
            }
        });
    }

});
