document.addEventListener('DOMContentLoaded', function () {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (el) {
        return new bootstrap.Tooltip(el)
    })

    var alerts = document.querySelectorAll('.alert-dismissible')
    alerts.forEach(function (alert) {
        setTimeout(function () {
            var bsAlert = new bootstrap.Alert(alert)
            bsAlert.close()
        }, 5000)
    })
});
