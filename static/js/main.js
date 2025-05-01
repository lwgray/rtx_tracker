/**
 * RTX 5090 Stock Tracker
 * Main JavaScript file for dashboard interactivity
 */

document.addEventListener('DOMContentLoaded', function() {
    // Enable tooltips everywhere
    const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
    
    // Auto-refresh the dashboard every 5 minutes
    setupAutoRefresh();
    
    // Initialize price filters
    initPriceFilters();
    
    // Handle notification settings
    setupNotificationSettings();
});

/**
 * Set up auto-refresh for the dashboard
 */
function setupAutoRefresh() {
    // Only enable auto-refresh on the main dashboard page
    if (window.location.pathname === '/') {
        const refreshInterval = 5 * 60 * 1000; // 5 minutes
        
        // Display a refresh countdown
        const refreshCountdown = document.getElementById('refresh-countdown');
        if (refreshCountdown) {
            let timeLeft = refreshInterval / 1000;
            
            // Update countdown every second
            setInterval(function() {
                timeLeft -= 1;
                if (timeLeft <= 0) {
                    timeLeft = refreshInterval / 1000;
                    window.location.reload();
                }
                
                const minutes = Math.floor(timeLeft / 60);
                const seconds = Math.floor(timeLeft % 60);
                refreshCountdown.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }, 1000);
        } else {
            // If no countdown element, just refresh silently
            setTimeout(function() {
                window.location.reload();
            }, refreshInterval);
        }
    }
}

/**
 * Initialize price range filters
 */
function initPriceFilters() {
    const priceFilterForm = document.getElementById('price-filter-form');
    if (priceFilterForm) {
        priceFilterForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const minPrice = document.getElementById('min-price').value;
            const maxPrice = document.getElementById('max-price').value;
            
            // Get all product rows
            const productRows = document.querySelectorAll('tr.product-row');
            
            // Filter products by price range
            productRows.forEach(row => {
                const priceCell = row.querySelector('td.product-price');
                if (!priceCell) return;
                
                // Extract numeric price value
                const priceText = priceCell.textContent.trim();
                const price = parseFloat(priceText.replace('$', '').replace(',', ''));
                
                // Apply filter
                if (
                    (minPrice === '' || price >= parseFloat(minPrice)) &&
                    (maxPrice === '' || price <= parseFloat(maxPrice))
                ) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
        
        // Reset button
        const resetButton = document.getElementById('reset-filter');
        if (resetButton) {
            resetButton.addEventListener('click', function() {
                document.getElementById('min-price').value = '';
                document.getElementById('max-price').value = '';
                
                // Show all rows
                document.querySelectorAll('tr.product-row').forEach(row => {
                    row.style.display = '';
                });
            });
        }
    }
}

/**
 * Setup notification settings form
 */
function setupNotificationSettings() {
    const notificationForm = document.getElementById('notification-settings');
    if (notificationForm) {
        notificationForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const priceThreshold = document.getElementById('price-threshold').value;
            
            // Save settings to localStorage
            localStorage.setItem('priceThreshold', priceThreshold);
            
            // Show confirmation message
            const alertBox = document.createElement('div');
            alertBox.className = 'alert alert-success alert-dismissible fade show';
            alertBox.innerHTML = `
                <strong>Success!</strong> Your notification settings have been updated.
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            `;
            
            notificationForm.prepend(alertBox);
            
            // Remove the alert after 3 seconds
            setTimeout(() => {
                alertBox.remove();
            }, 3000);
        });
        
        // Load saved settings
        const savedThreshold = localStorage.getItem('priceThreshold');
        if (savedThreshold) {
            document.getElementById('price-threshold').value = savedThreshold;
        }
    }
}