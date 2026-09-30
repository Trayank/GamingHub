// Studio Elena Rostova - Custom JS Interactivity

document.addEventListener('DOMContentLoaded', function () {
    // Handle Art Class Seat Reservation Modal
    const reserveModal = document.getElementById('reserveSeatModal');
    if (reserveModal) {
        reserveModal.addEventListener('show.bs.modal', function (event) {
            const button = event.relatedTarget;
            if (button) {
                const classId = button.getAttribute('data-class-id');
                const classTitle = button.getAttribute('data-class-title');
                const classPrice = button.getAttribute('data-class-price');
                const seatsAvailable = button.getAttribute('data-seats-available');

                const modalClassIdInput = reserveModal.querySelector('#id_class_id');
                const modalTitleSpan = reserveModal.querySelector('#modalClassTitle');
                const modalPriceSpan = reserveModal.querySelector('#modalClassPrice');
                const modalSeatsInput = reserveModal.querySelector('#id_seats_count');

                if (modalClassIdInput) modalClassIdInput.value = classId;
                if (modalTitleSpan) modalTitleSpan.textContent = classTitle;
                if (modalPriceSpan) modalPriceSpan.textContent = 'Rs ' + classPrice;
                if (modalSeatsInput && seatsAvailable) {
                    modalSeatsInput.setAttribute('max', seatsAvailable);
                }
            }
        });
    }

    // Auto-dismiss alert messages after 6 seconds
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 6000);
    });
});
