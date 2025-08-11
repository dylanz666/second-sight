// 趋势图模块 - 内存、CPU、网络延迟趋势图功能

// 绘制内存使用率趋势图
function drawMemoryTrendChart() {
    const canvas = document.getElementById('memory-trend-chart');
    if (!canvas || memoryTrendData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // 清除画布
    ctx.clearRect(0, 0, width, height);

    // 固定数据范围为0-100
    const minValue = 0;
    const maxValue = 100;
    const range = maxValue - minValue;

    // 绘制网格线
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = (height / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // 绘制趋势线
    ctx.strokeStyle = '#667eea';
    ctx.lineWidth = 2;
    ctx.beginPath();

    memoryTrendData.forEach((value, index) => {
        const x = (index / (memoryTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // 绘制数据点
    ctx.fillStyle = '#667eea';
    memoryTrendData.forEach((value, index) => {
        const x = (index / (memoryTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
    });
}

// 绘制CPU使用率趋势图
function drawCpuTrendChart() {
    const canvas = document.getElementById('cpu-trend-chart');
    if (!canvas || cpuTrendData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // 清除画布
    ctx.clearRect(0, 0, width, height);

    // 固定数据范围为0-100
    const minValue = 0;
    const maxValue = 100;
    const range = maxValue - minValue;

    // 绘制网格线
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = (height / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // 绘制趋势线
    ctx.strokeStyle = '#56ab2f';
    ctx.lineWidth = 2;
    ctx.beginPath();

    cpuTrendData.forEach((value, index) => {
        const x = (index / (cpuTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // 绘制数据点
    ctx.fillStyle = '#56ab2f';
    cpuTrendData.forEach((value, index) => {
        const x = (index / (cpuTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
    });
}

// 绘制网络延迟趋势图
function drawNetworkLatencyTrendChart() {
    const canvas = document.getElementById('network-latency-trend-chart');
    if (!canvas || networkLatencyTrendData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    // 清除画布
    ctx.clearRect(0, 0, width, height);

    // 固定数据范围为0-最大延迟值
    const minValue = 0;
    const maxValue = Math.max(...networkLatencyTrendData, 50); // 至少50ms，确保有足够范围
    const range = maxValue - minValue;

    // 绘制网格线
    ctx.strokeStyle = '#e0e0e0';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
        const y = (height / 4) * i;
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(width, y);
        ctx.stroke();
    }

    // 绘制趋势线
    ctx.strokeStyle = '#f39c12';
    ctx.lineWidth = 2;
    ctx.beginPath();

    networkLatencyTrendData.forEach((value, index) => {
        const x = (index / (networkLatencyTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        if (index === 0) {
            ctx.moveTo(x, y);
        } else {
            ctx.lineTo(x, y);
        }
    });

    ctx.stroke();

    // 绘制数据点
    ctx.fillStyle = '#f39c12';
    networkLatencyTrendData.forEach((value, index) => {
        const x = (index / (networkLatencyTrendData.length - 1)) * width;
        const y = height - ((value - minValue) / range) * height;

        ctx.beginPath();
        ctx.arc(x, y, 2, 0, 2 * Math.PI);
        ctx.fill();
    });
}

// 添加内存使用率数据点
function addMemoryDataPoint(value) {
    if (typeof value === 'number' && !isNaN(value)) {
        memoryTrendData.push(value);

        // 保持最多 MAX_TREND_POINTS 个数据点
        if (memoryTrendData.length > MAX_TREND_POINTS) {
            memoryTrendData.shift();
        }

        // 重新绘制趋势图
        drawMemoryTrendChart();

        // 更新工具提示
        updateTrendChartTooltip();
    }
}

// 添加CPU使用率数据点
function addCpuDataPoint(value) {
    if (typeof value === 'number' && !isNaN(value)) {
        cpuTrendData.push(value);

        // 保持最多 MAX_TREND_POINTS 个数据点
        if (cpuTrendData.length > MAX_TREND_POINTS) {
            cpuTrendData.shift();
        }

        // 重新绘制趋势图
        drawCpuTrendChart();

        // 更新工具提示
        updateTrendChartTooltip();
    }
}

// 添加网络延迟数据点
function addNetworkLatencyDataPoint(value) {
    if (typeof value === 'number' && !isNaN(value)) {
        networkLatencyTrendData.push(value);

        // 保持最多 MAX_TREND_POINTS 个数据点
        if (networkLatencyTrendData.length > MAX_TREND_POINTS) {
            networkLatencyTrendData.shift();
        }

        // 重新绘制趋势图
        drawNetworkLatencyTrendChart();

        // 更新工具提示
        updateTrendChartTooltip();
    }
}

// 更新趋势图工具提示
function updateTrendChartTooltip() {
    const memoryCanvas = document.getElementById('memory-trend-chart');
    const cpuCanvas = document.getElementById('cpu-trend-chart');
    const networkLatencyCanvas = document.getElementById('network-latency-trend-chart');

    // 更新内存趋势图工具提示
    if (memoryCanvas) {
        if (memoryTrendData.length > 0) {
            const latest = memoryTrendData[memoryTrendData.length - 1];
            const min = Math.min(...memoryTrendData);
            const max = Math.max(...memoryTrendData);
            const avg = (memoryTrendData.reduce((a, b) => a + b, 0) / memoryTrendData.length).toFixed(1);

            memoryCanvas.title = `内存使用率趋势\n最新: ${latest}%\n最高: ${max}%\n最低: ${min}%\n平均: ${avg}%`;
        } else {
            memoryCanvas.title = '内存使用率趋势\n暂无数据';
        }
    }

    // 更新CPU趋势图工具提示
    if (cpuCanvas) {
        if (cpuTrendData.length > 0) {
            const latest = cpuTrendData[cpuTrendData.length - 1];
            const min = Math.min(...cpuTrendData);
            const max = Math.max(...cpuTrendData);
            const avg = (cpuTrendData.reduce((a, b) => a + b, 0) / cpuTrendData.length).toFixed(1);

            cpuCanvas.title = `CPU使用率趋势\n最新: ${latest}%\n最高: ${max}%\n最低: ${min}%\n平均: ${avg}%`;
        } else {
            cpuCanvas.title = 'CPU使用率趋势\n暂无数据';
        }
    }

    // 更新网络延迟趋势图工具提示
    if (networkLatencyCanvas) {
        if (networkLatencyTrendData.length > 0) {
            const latest = networkLatencyTrendData[networkLatencyTrendData.length - 1];
            const min = Math.min(...networkLatencyTrendData);
            const max = Math.max(...networkLatencyTrendData);
            const avg = (networkLatencyTrendData.reduce((a, b) => a + b, 0) / networkLatencyTrendData.length).toFixed(1);

            networkLatencyCanvas.title = `网络延迟趋势\n最新: ${latest}ms\n最高: ${max}ms\n最低: ${min}ms\n平均: ${avg}ms`;
        } else {
            networkLatencyCanvas.title = '网络延迟趋势\n暂无数据';
        }
    }
} 