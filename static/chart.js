// Initial chart setup
const chartStyle = {
    layout: {
        background: { type: 'solid', color: '#11111100' },
        textColor: '#DDDDDD',
        fontFamily: 'Outfit'
    },
    grid: {
        vertLines: {
            color: '#AAAAAA11',
        },
        horzLines: {
            color: '#AAAAAA11',
        },
    },
    priceScale: {
        autoScale: true,
    },
    timeScale: {
        barSpacing: 10,
        timeVisible: true,
        rightOffset: 10
    },
    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
    },
    width: document.getElementById('chart').clientWidth,
    height: document.getElementById('chart').clientHeight,
};

const chart = LightweightCharts.createChart(document.getElementById('chart'), chartStyle);
const candlestickSeries = chart.addCandlestickSeries();

document.getElementById('chart-header').addEventListener('change', () => {
    exchange = document.getElementById('selected-exchange').textContent;
    symbol = document.getElementById('selected-symbol').textContent;
    timeframe =  document.getElementById('selected-timeframe').value;
    length = 25000;
    polling_frequency = 1;

    fetch(`/set_chart_header?exchange=${exchange}&symbol=${symbol}&timeframe=${timeframe}&length=${length}&polling_frequency=${polling_frequency}`)
    fetchData(exchange, symbol, timeframe, length)
})

function autoUpdateChart() {
    exchange = document.getElementById('selected-exchange') != undefined ? document.getElementById('selected-exchange').textContent : undefined;
    symbol = document.getElementById('selected-symbol') != undefined ? document.getElementById('selected-symbol').textContent : undefined;
    timeframe =  document.getElementById('selected-timeframe') != undefined ? document.getElementById('selected-timeframe').value : undefined;
    // length = 25000;
    polling_frequency = 1;
    logical_range = chart.timeScale().getVisibleLogicalRange();
    toValue = logical_range !== null ? Math.ceil(logical_range.to) : 0
    fromValue = logical_range !== null ? Math.ceil(logical_range.from) : 0;
    visibleRange = toValue - fromValue;
    rangeCenter = fromValue + (visibleRange / 2);
    let length1;
    if (visibleRange !== 0) {
        length1 = visibleRange * 3
    } else { length1 = 5000 }

    if (document.getElementById('chart-header').innerHTML == '') { setTimeout(autoUpdateChart, polling_frequency*1000) }
    else {
        fetchData(exchange, symbol, timeframe, length1)
        setTimeout(autoUpdateChart, polling_frequency*1000)
    }
}

// Fetch data function
function fetchData(exchange, symbol, timeframe, length) {
    fetch(`/chart_data?exchange=${exchange}&symbol=${symbol}&timeframe=${timeframe}&length=${length}`)
        .then(response => response.json())
        .then(data => {
            candlestickSeries.setData(data.candlestick_data);
            if (data.candlestick_data[data.candlestick_data.length-1].close < 1) {
                candlestickSeries.applyOptions({
                    priceFormat: {
                        type: 'price',
                        precision: 6,
                        minMove: 0.000001,
                    },
                });
            }
            else {
                candlestickSeries.applyOptions({
                    priceFormat: {
                        type: 'price',
                        precision: 2,
                        minMove: 0.01,
                    },
                });
            }
        })
}

window.addEventListener('load', () => {
    fetch(`/get_chart_header`)
    .then(response => response.json())
    .then(data => {
        exchange = data.exchange
        symbol = data.symbol
        timeframe = data.timeframe
        length = data.length
        fetchData(exchange, symbol, timeframe, length);
        autoUpdateChart();
    })
});

window.addEventListener('resize', () => {
    chart.resize(document.getElementById('chart').clientWidth, document.getElementById('chart').clientHeight)
});