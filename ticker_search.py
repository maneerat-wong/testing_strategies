import requests
import pandas as pd
import json
import logging

API_KEY = "IG0FA0FSNFBRNI78"
SERACH_URL = f"https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={API_KEY}"
new = "NZ1OIONBN5J6O92X"

def get_all_ticker_from_api():
    """ There is a request limit for the free tier so I will not use this for the demo"""
    download = requests.get(SERACH_URL)
    decoded_content = download.content.decode('utf-8')
    ticket_list = [row.split(',') for row in decoded_content.splitlines()]
    df = pd.DataFrame(ticket_list[1:], columns=ticket_list[0])
    if len(df) == 0:
        return None
    else:
        return list(df['symbol'])


def get_price_data_from_API(ticker):
    TICKER_DATA_URL = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&outputsize=full&symbol={ticker}&apikey={API_KEY}" 
    r = requests.get(TICKER_DATA_URL)
    data = r.json()
    return data


def get_price_data_from_json(ticker):
    with open(f'{ticker}_2024-12-20.json','r') as f:
        data = json.load(f)
    return data

def get_df_from_ticker_data(ticker):
    data = get_price_data_from_json(ticker)
    days = []
    for k, _ in data['Time Series (Daily)'].items():
        days.append(k)
    df = pd.DataFrame({'date':days})
    df.index = pd.to_datetime(df['date'])
    return df

def get_strategy(ticker, pct_volume_breakout, daily_change_threshold, holding_period, rolling_window, start_date, end_date):
    data = get_price_data_from_json(ticker)
    days = []
    close_price = []
    open_price = []
    high_price = []
    low_price = []
    volume = []
    for k, v in data['Time Series (Daily)'].items():
        days.append(k)
        close_price.append(float(v['4. close']))
        high_price.append(float(v['2. high']))
        low_price.append(float(v['3. low']))
        open_price.append(float(v['1. open']))
        volume.append(int(v['5. volume']))
    df = pd.DataFrame({'date':days , 'open price': open_price,'close price': close_price, 'high price':high_price, 'low price':low_price, 'volume':volume})
    df.index = pd.to_datetime(df.date)
    df.sort_index(ascending=True, inplace=True)
    df = df[(df.index.date >= start_date) & (df.index.date <= end_date)]
    df['rolling volume'] = df['volume'].rolling(window=rolling_window).mean()
    df[f'Avg. {rolling_window} days volume'] = df['rolling volume'].shift(1)
    df['% volume change'] = (df['volume'] - df[f'Avg. {rolling_window} days volume'])/df[f'Avg. {rolling_window} days volume'] * 100
    df['yesterday close price'] = df['close price'].shift(1)
    df['% price change'] = (df['open price'] - df['yesterday close price'])/df['yesterday close price'] * 100
    df['condition match'] = (df['% volume change'] > pct_volume_breakout) & (df['% price change'] > daily_change_threshold) 
    df['price after 10 days'] = df['close price'].shift(-holding_period)
    df['sell date'] = pd.to_datetime(df['date'].shift(-holding_period))
    df.drop(columns=['date'], inplace=True)
    df['% pnl after selling'] = (df['price after 10 days'] - df['close price'])/df['close price']
    return df

def crete_pnl_df(buy_day_stats, df):
    sell_dict = dict(zip(buy_day_stats['sell date'], buy_day_stats['accumulative pnl']))
    sell_price = dict(zip(buy_day_stats['sell date'], buy_day_stats['price after 10 days']))
    buy_dict = dict(zip(buy_day_stats.index, buy_day_stats['close price']))
    pnl = pd.DataFrame({'date':df.index})
    pnl['pct change'] = pnl['date'].map(sell_dict)
    pnl['sell price'] = pnl['date'].map(sell_price)
    pnl['sell'] = ~pnl['pct change'].isna()
    pnl['pct change'] = pnl['pct change'].ffill().fillna(0)
    pnl['pct change'] = pnl['pct change'].apply(lambda x: '{:.2f}'.format(x))
    pnl['buy price'] = pnl['date'].map(buy_dict)
    pnl['buy condition'] = ~pnl['buy price'].isna()
    return pnl

def create_buy_day_stats(df):
    buy_day_stats = df[df['condition match'] == True].drop(columns=['rolling volume','condition match','high price','low price'])
    buy_day_stats['accumulative pnl'] = (1 + buy_day_stats['% pnl after selling']).cumprod() - 1
    return buy_day_stats
    
def format_df_before_download(buy_day_stats, rolling_window):
    for c in ['volume', f'Avg. {rolling_window} days volume']:
        buy_day_stats[c] = buy_day_stats[c].apply(lambda x: '{:,.2f}'.format(x))
    for c in ['% volume change', '% price change', '% pnl after selling','accumulative pnl']:
        buy_day_stats[c] = buy_day_stats[c].apply(lambda x: '{:.4f}'.format(x))
    return buy_day_stats