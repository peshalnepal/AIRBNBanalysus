document.addEventListener('DOMContentLoaded', () => {
    const charts = JSON.parse(document.getElementById('chart-data').textContent);
    let currentChartIndex = 0;

    function loadChart() {
        const chartFrame = document.getElementById('chart-frame');
        const description = document.getElementById('description');
        chartFrame.src = charts[currentChartIndex].url;
        description.innerText = charts[currentChartIndex].description;
    }

    function prevChart() {
        currentChartIndex = (currentChartIndex - 1 + charts.length) % charts.length;
        loadChart();
    }

    function nextChart() {
        currentChartIndex = (currentChartIndex + 1) % charts.length;
        loadChart();
    }

    document.querySelector('.arrow.left').addEventListener('click', prevChart);
    document.querySelector('.arrow.right').addEventListener('click', nextChart);

    loadChart();
});
