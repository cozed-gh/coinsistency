let initialY = null;
let searchQuery = undefined
let searchPages = undefined
let currentSearchPage = 1;
let searchTimeout;
const hits = document.getElementById('result-hits');
const currentPage = document.getElementById('result-current');
const pages = document.getElementById('result-pages');
const ohlcvSince = document.getElementById('ohlcv-since');

ohlcvSince.addEventListener('change', () => {
    let since = ohlcvSince.value;
    fetch(`/set_ohlcv?ohlcv-since=${since}`)
})

document.getElementById('footer-handle').addEventListener('mousedown', (event) => {
  initialY = event.clientY;
});

document.addEventListener('mouseup', () => {
  initialY = null;
});

document.addEventListener('mousemove', (event) => {
  if (initialY !== null) {
    let newFooterHeight = Math.min(Math.max(window.innerHeight - event.clientY, 52), 720);
    let newChartHeight = window.innerHeight - newFooterHeight - 74;
    document.getElementById('footer').style.height = `${newFooterHeight}px`;
    document.getElementById('footer-handle').style.bottom = `${newFooterHeight}px`
    document.getElementById('chart').style.height = `${newChartHeight}px`;
    chart.resize(document.getElementById('chart').clientWidth, document.getElementById('chart').clientHeight);
  }
});

document.getElementById('search-query').addEventListener('keyup', (event) => {
    let newSearchQuery = event.target.value; // Get the current value of the input field
  
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        searchMarkets(newSearchQuery);
    }, 500);
  });

document.getElementById('search-result').addEventListener('wheel', (event) => {
if (event.deltaY > 0) {
    nextSearchPage()
    } else if (event.deltaY < 0) {
        previousSearchPage()
    }
});

function showHide(id) {
    let element = document.getElementById(id)
    if (element.style.display === 'none' || element.style.display === '') { element.style.display = 'block' }
    else { 
        element.style.display = 'none' 
    }
};

function closeDiv(id) {
    let element = document.getElementById(id)
    element.style.display = 'none'
};

function searchMarkets(query = searchQuery, page = 1, pageSize = 15) {
    if (searchQuery === undefined || searchQuery !== query) {
        currentSearchPage = 1
        searchQuery = query
    } else { currentSearchPage = page}
    fetch(`/search_market?query=${query}&page=${page}`)
        .then(response => response.json())
        .then(data => {
            const resultsDiv = document.getElementById('search-result');
            resultsDiv.innerHTML = '';

            // Check if there are more results
            searchPages = Math.ceil(data.length / pageSize);

            hits.innerHTML = `<p>Hits: ${data.length}</p>`;
            pages.innerHTML = `<p>Pages: ${searchPages}</p>`;
            currentPage.innerHTML = pageEnumStyle(currentSearchPage, searchPages)
            document.getElementById('prevPage').innerHTML = '<span class="material-symbols-outlined highlight" onclick="previousSearchPage()">arrow_back_ios</span>'
            document.getElementById('nextPage').innerHTML = '<span class="material-symbols-outlined highlight" onclick="nextSearchPage()">arrow_forward_ios</span>'

            let begin = (page-1)*pageSize
            for (i=0; i<pageSize; i++) {
                let symbolExchange = data[begin+i][0]
                let marketSymbol = data[begin+i][1]

                const marketElement = document.createElement('div');
                marketElement.classList.add('market-result');

                const iconElement = document.createElement('span');
                iconElement.classList.add('material-symbols-outlined');
                iconElement.textContent = 'bar_chart';
                iconElement.style.flex = '1';
                iconElement.style.textAlign = 'center';
                marketElement.appendChild(iconElement);

                const exchangeElement = document.createElement('span');
                exchangeElement.textContent = symbolExchange;
                exchangeElement.style.flex = '2';
                marketElement.appendChild(exchangeElement);

                const marketSymbolElement = document.createElement('span');
                marketSymbolElement.textContent = marketSymbol;
                marketSymbolElement.style.flex = '4';
                marketElement.appendChild(marketSymbolElement);

                const addMarketIcon = document.createElement('span');
                addMarketIcon.classList.add('material-symbols-outlined');
                addMarketIcon.classList.add('highlight');
                addMarketIcon.textContent = 'add';
                addMarketIcon.style.flex = '1';
                addMarketIcon.addEventListener('click', (event) => {
                    fetch(`/add_market?exchange=${symbolExchange}&symbol=${marketSymbol}`)
                        .then(response => response.json()) // Handle response data (optional) NOTIFY!
                        .then(data => {
                            // Handle the response data
                            console.log('Market added successfully:', data);
                      
                            // Send the data to your notification function
                            showNotification(data.message); // Assuming the response has a 'message' property
                            updateConfig()
                          })
                        .catch(error => console.error('Error adding market:', error));
                })
                iconElement.style.textAlign = 'center';
                marketElement.appendChild(addMarketIcon);

                resultsDiv.appendChild(marketElement);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
}

function nextSearchPage() {
    if (currentSearchPage == searchPages) { return }
    currentSearchPage = Math.min(Math.max(currentSearchPage+1, 1), searchPages)
    searchMarkets(searchQuery, currentSearchPage);
}

function previousSearchPage() {
    if (currentSearchPage == 1) { return }
    currentSearchPage = Math.max(currentSearchPage-1, 1)
    searchMarkets(searchQuery, currentSearchPage);
}

function pageEnumStyle(page, pages) {
    styling = `<p>`
    let startPage = 1;
    let endPage = Math.min(9, pages);

    if (page > 5) {
        startPage = Math.max(page - 4, 1);
        endPage = Math.min(page + 4, pages);
    }
    if (page >= pages-2) {
        startPage = Math.max(pages - 8, 1);
    }

    for (i=startPage; i<=endPage; i++) {
        if (i != page) {
            styling += `  ${i}  `
        } else {
            styling += `<strong> ${i} </strong>`
        }
    }
    styling += `</p>`

    return styling
}

function showNotification(message) {
    const notificationContainer = document.querySelector('.notification-container');
    const notification = document.createElement('div');
    notification.classList.add('notification');   
  
    notification.textContent = message;
    notificationContainer.appendChild(notification);
    notificationContainer.classList.add('visible')
  
    setTimeout(() => {
        notification.remove(); 
    }, 3000);
    if (notificationContainer.children.length === 0) {
        notificationContainer.classList.remove('visible'); 
    }
  }

  function updateConfig() {
    fetch('/load_config')
        .then(response => response.json())
        .then(data => {
            ohlcvSince.value = data['ohlcv']

            const marketsContainer = document.getElementById('user-markets')
            marketsContainer.innerHTML = ''
            for (i=0; i<data['markets'].length; i++) {
                let exchange = data['markets'][i].exchange
                let symbol = data['markets'][i].symbol

                const marketContainer = document.createElement('div')
                marketContainer.id = 'user-market'

                const iconElement = document.createElement('span');
                iconElement.classList.add('material-symbols-outlined');
                iconElement.textContent = 'bar_chart';
                iconElement.style.flex = '0.3';
                iconElement.style.flexShrink = '0';
                iconElement.style.textAlign = 'center';
                iconElement.style.color = '#FFC'
                iconElement.addEventListener('click', (event) => {
                    updateChartHeader(exchange, symbol)
                })
                marketContainer.appendChild(iconElement);

                const nameElement = document.createElement('div');
                nameElement.classList.add('market-label')
                nameElement.innerHTML = `<p style="text-align: left; margin-top: 5px;">${exchange}<br><strong style="font-size: 18px">${symbol}</strong></p>`
                nameElement.style.flex = '2';
                nameElement.style.overflow = 'hidden';
                nameElement.addEventListener('click', (event) => {
                    updateChartHeader(exchange, symbol)
                })
                marketContainer.appendChild(nameElement)

                const removeElement = document.createElement('span');
                removeElement.classList.add('material-symbols-outlined');
                removeElement.classList.add('highlight');
                removeElement.style.textAlign = 'right';
                removeElement.style.marginRight = '10px';
                removeElement.style.fontSize = '18px';
                removeElement.textContent = 'delete';
                removeElement.style.flex = '0.3';
                removeElement.style.flexShrink = '0';
                removeElement.addEventListener('click', (event) => {
                    fetch(`/remove_market?exchange=${exchange}&symbol=${symbol}`)
                        .then(response => response.json()) // Handle response data (optional) NOTIFY!
                        .then(data => {
                            // Handle the response data
                            console.log('Market removed from list successfully:', data);
                      
                            // Send the data to your notification function
                            showNotification(data.message); // Assuming the response has a 'message' property
                            updateConfig();
                          })
                        .catch(error => console.error('Error adding market:', error));
                })
                marketContainer.appendChild(removeElement)

                marketsContainer.appendChild(marketContainer)

                // markets[0].exchange
            }
        })
        .catch(error => {
            console.error('Error fetching config.json:', error);
        })
  }

function updateChartHeader(exchange, symbol, timeframe, length, polling_frequency) {
    fetch(`/get_chart_header`)
    .then(response => response.json())
    .then(data => {
        exchange = exchange !== undefined ? exchange : data.exchange
        symbol = symbol !== undefined ? symbol : data.symbol
        timeframe = timeframe !== undefined ? timeframe : data.timeframe
        length = length !== undefined ? length : data.length
        polling_frequency = polling_frequency !== undefined ? polling_frequency : data.polling_frequency

        const headerContainer = document.getElementById('chart-header')
        headerContainer.style.zIndex = '3'
        headerContainer.style.display = 'flex'
        headerContainer.style.alignItems = 'center'
        headerContainer.innerHTML = ''

        const iconElement = document.createElement('span');
        iconElement.classList.add('material-symbols-outlined');
        iconElement.textContent = 'bar_chart';
        iconElement.style.width = '40px';
        iconElement.style.flexShrink = '0';
        iconElement.style.textAlign = 'center';
        iconElement.style.color = '#FFC';
        headerContainer.appendChild(iconElement)

        const nameElement = document.createElement('div');
        nameElement.classList.add('market-label')
        nameElement.innerHTML = `<p style="text-align: left; margin-top: 5px;"><span id="selected-exchange">${exchange}</span><br><strong style="font-size: 18px" id="selected-symbol">${symbol}</strong></p>`
        nameElement.style.flex = '0.1';
        headerContainer.appendChild(nameElement)

        const timeframeElement = document.createElement('div')
        timeframeElement.classList.add('timeframes')
        timeframeElement.style.flex = '1';
        timeframeElement.style.verticalAlign = 'center'
        timeframeElement.innerHTML = `
            <span class="custom-dropdown">
                <select id="selected-timeframe">
                    <option>1min</option>
                    <option>2min</option>  
                    <option>3min</option>
                    <option>5min</option>
                    <option>10min</option>
                    <option>15min</option>
                    <option>20min</option>
                    <option>30min</option>
                    <option>1h</option>
                    <option>2h</option>
                    <option>3h</option>
                    <option>4h</option>
                    <option>6h</option>
                    <option>8h</option>
                    <option>12h</option>
                    <option>1D</option>
                    <option>2D</option>
                    <option>3D</option>
                </select>
            </span>`;
        headerContainer.appendChild(timeframeElement)
        const selectedTimeframeDropdown = headerContainer.querySelector('#selected-timeframe');
        selectedTimeframeDropdown.querySelectorAll('option').forEach(option => {
            if (option.textContent.toLowerCase() === timeframe.toLowerCase()) {
            option.selected = true; // Set the matching option as selected
            } else {
            option.selected = false; // Unset other options
            }
        });
    })
}

window.addEventListener('load', () => {
    updateChartHeader();
    updateConfig();
})