const memoryUsageElement = document.getElementById('memory-usage');
const numClientsElement = document.getElementById('num-clients');
const numCamerasElement = document.getElementById('num-cameras');
const ctx = document.getElementById('metricsChart').getContext('2d');

let metricsChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Memory Usage (MB)',
            data: [],
            borderColor: 'rgba(75, 192, 192, 1)',
            borderWidth: 2,
            fill: false
        }]
    },
    options: {
        scales: {
            y: {
                beginAtZero: true
            }
        }
    }
});

async function fetchMetrics() {
    try {
        const response = await fetch('http://127.0.0.1:8000/metrics'); // URL вашего API
        const data = await response.json();

        // Обновление метрик на странице
        memoryUsageElement.textContent = data.memory_usage_mb.toFixed(2);
        numClientsElement.textContent = data.num_clients;
        numCamerasElement.textContent = data.num_cameras;

        // Обновление графика
        const currentTime = new Date().toLocaleTimeString();
        metricsChart.data.labels.push(currentTime);
        metricsChart.data.datasets[0].data.push(data.memory_usage_mb);

        if (metricsChart.data.labels.length > 10) {
            metricsChart.data.labels.shift();
            metricsChart.data.datasets[0].data.shift();
        }

        metricsChart.update();
    } catch (error) {
        console.error('Error fetching metrics:', error);
    }
}

// Запрос метрик каждые 5 секунд
// setInterval(fetchMetrics, 5000);
// fetchMetrics(); // Первоначальный вызов