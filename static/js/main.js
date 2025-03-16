document.addEventListener('DOMContentLoaded', function() {
    // Initialize withdraw buttons
    const withdrawButtons = document.querySelectorAll('.withdraw-btn');
    const withdrawModal = new bootstrap.Modal(document.getElementById('withdrawModal'));
    const autoSearchModal = new bootstrap.Modal(document.getElementById('autoSearchModal'));

    // Handle withdrawal button clicks
    withdrawButtons.forEach(button => {
        button.addEventListener('click', function() {
            const fundId = this.dataset.fundId;
            const amount = this.dataset.amount;

            document.getElementById('fundId').value = fundId;
            document.getElementById('withdrawAmount').textContent = `$${parseFloat(amount).toFixed(2)}`;
            withdrawModal.show();
        });
    });

    // Handle withdrawal confirmation
    document.getElementById('confirmWithdraw').addEventListener('click', function() {
        const form = document.getElementById('withdrawForm');
        const formData = new FormData(form);

        fetch('/admin/withdraw', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                alert('Withdrawal processed successfully');
                location.reload();
            }
            withdrawModal.hide();
        })
        .catch(error => {
            alert('An error occurred during withdrawal');
            console.error('Error:', error);
        });
    });

    // Handle auto-search functionality
    const startAutoSearchBtn = document.getElementById('startAutoSearch');
    if (startAutoSearchBtn) {
        startAutoSearchBtn.addEventListener('click', function() {
            fetch('/admin/start-auto-search', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    autoSearchModal.show();
                    // Update button state
                    startAutoSearchBtn.disabled = true;
                    startAutoSearchBtn.innerHTML = '<i data-feather="check-circle"></i> Auto-Search Active';
                    feather.replace();
                }
            })
            .catch(error => {
                alert('Error starting auto-search');
                console.error('Error:', error);
            });
        });
    }

    // Refresh funds list periodically when auto-search is active
    let autoSearchActive = false;
    function refreshFundsList() {
        if (!autoSearchActive) return;

        fetch('/admin/check-new-funds')
            .then(response => response.json())
            .then(data => {
                if (data.newFunds) {
                    location.reload();
                }
            });
    }

    // Check for new funds every 30 seconds
    setInterval(refreshFundsList, 30000);

    // Handle aged funds processing (admin only)
    const processAgedFundsBtn = document.getElementById('processAgedFunds');
    if (processAgedFundsBtn) {
        processAgedFundsBtn.addEventListener('click', function() {
            if (!confirm('Are you sure you want to process all aged funds?')) {
                return;
            }

            fetch('/admin/process-aged-funds', {
                method: 'POST'
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    alert('Aged funds processed successfully');
                    location.reload();
                }
            })
            .catch(error => {
                alert('An error occurred while processing aged funds');
                console.error('Error:', error);
            });
        });
    }
});