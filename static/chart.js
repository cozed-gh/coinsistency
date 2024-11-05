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

let exchange, symbol, timeframe;
var dataLength = 250;


window.addEventListener('load', () => {
    fetch(`/get_chart_defaults`)
    .then(response => response.json())
    .then(data => {
        exchange = data.exchange
        symbol = data.symbol
        timeframe = data.timeframe
        fetchData(exchange, symbol, timeframe);
        dataPolling()
    })
});

chart.timeScale().subscribeVisibleLogicalRangeChange(onVisibleLogicalRangeChanged);

document.getElementById('chart-header').addEventListener('change', () => {
    exchange = document.getElementById('selected-exchange').textContent;
    symbol = document.getElementById('selected-symbol').textContent;
    timeframe =  document.getElementById('selected-timeframe').value;
    updateMarket()
})

// Fetch data function
async function fetchData(exchange, symbol, timeframe) {
    if (!exchange || !symbol || !timeframe) { return }
    dataLength = dataLength === undefined ? 200 : dataLength
    fetch(`/chart_data?exchange=${exchange}&symbol=${symbol}&timeframe=${timeframe}&length=${dataLength}`)
    .then(response => response.json())
    .then(data => {
        candlestickSeries.setData(data.candlestick_data);
        if (data.candlestick_data[data.candlestick_data.length-1].close < 1) {
            candlestickSeries.applyOptions({
                priceFormat: {
                    type: 'price',
                    precision: 7,
                    minMove: 0.0000001,
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

window.addEventListener('resize', () => {
    chart.resize(document.getElementById('chart').clientWidth, document.getElementById('chart').clientHeight)
});

let updatingChart = false
async function onVisibleLogicalRangeChanged(newVisibleLogicalRange) {
    if (updatingChart === false) {
        updatingChart = true
        range = Math.ceil((newVisibleLogicalRange.to - newVisibleLogicalRange.from));
        triggerLength = Math.ceil(range / 2)

        const barsInfo = candlestickSeries.barsInLogicalRange(newVisibleLogicalRange);
        if (barsInfo) {
            let newDataLength = Math.ceil(barsInfo.barsAfter + range * 2)
            if (barsInfo.barsBefore < triggerLength && dataLength !== newDataLength) {
                dataLength = newDataLength
                await fetchData(exchange, symbol, timeframe)
            }
            if (barsInfo.barsAfter < 0 && dataLength !== newDataLength) {
                dataLength = newDataLength
                await fetchData(exchange, symbol, timeframe)
            }
            chart.timeScale().setVisibleLogicalRange(newVisibleLogicalRange);
        }
        updatingChart = false
    }
}

function updateMarket() {
    headerExchange = document.getElementById('selected-exchange').textContent
    headerSymbol = document.getElementById('selected-symbol').textContent
    headerTimeframe = document.getElementById('selected-timeframe').value

    exchange = headerExchange === "" ? exchange : headerExchange;
    symbol = headerSymbol === "" ? symbol : headerSymbol;
    timeframe =  headerTimeframe === "" ? timeframe : headerTimeframe;
    setDefaults(exchange, symbol, timeframe)
    fetchData(exchange, symbol, timeframe)
}

function setDefaults(exchange, symbol, timeframe) {
    fetch(`/set_chart_defaults?exchange=${exchange}&symbol=${symbol}&timeframe=${timeframe}`)
}

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms))
}

async function dataPolling() {
    headerExchange = document.getElementById('selected-exchange').textContent
    headerSymbol = document.getElementById('selected-symbol').textContent
    headerTimeframe = document.getElementById('selected-timeframe').value

    exchange = headerExchange === "" ? exchange : headerExchange;
    symbol = headerSymbol === "" ? symbol : headerSymbol;
    timeframe =  headerTimeframe === "" ? timeframe : headerTimeframe;
    fetchData(exchange, symbol, timeframe)
    await sleep(500)
    dataPolling()
}