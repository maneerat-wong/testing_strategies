import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from ticker_search import get_strategy, get_df_from_ticker_data, crete_pnl_df, create_buy_day_stats, format_df_before_download

def reset_date_input(ticker):
    data = get_df_from_ticker_data(ticker)
    start_date = st.date_input('Start date to test the strategy', min_value=data.index.min(), max_value=data.index.max(), value=data.index.min())
    end_date = st.date_input('End date to test the strategy', min_value=start_date, max_value=data.index.max(), value=data.index.max())
    return start_date, end_date

st.set_page_config(
    page_title="Trading Strategy Testing",
    layout="wide"
) 
st.write("""
        # We are going to test some trading strategies. 
        """)

st.text("We are going to buy a stock if a stock has a daily volume more than X% over the last 20 days AND the price is up at least Y% compared to the previous day")

availble_ticker = ['AAPL','AMZN','GME','MSFT','TSLA','VOO','NVDA','GOOG']
ticker = st.selectbox("Please select the ticker", availble_ticker, placeholder="Search Ticker...")
if ticker:
    start_date, end_date = reset_date_input(ticker)

pct_volume_breakout = st.text_input("Please type the percentage volume breakout (X)", placeholder="200")
daily_change_threshold = st.text_input("Please type the threshold for the percentage change of the daily close price (Y)", placeholder=2)
holding_period = st.text_input("Please type the number of days that you will hold the stock after buying at the day of breakout as a whole number (Z)", placeholder=10)
rolling_window = 20


if st.button("Test the strategy. Let's see whether this strategy is profitable"):
    # Test the input
    if len(pct_volume_breakout) == 0 or len(daily_change_threshold) == 0 or len(holding_period) == 0:
        st.text("The input is incorrect. Please make sure that you type in all inputs")
    elif not holding_period.isdigit() and holding_period < 1:
        st.text("Please type the holding period as a positive whole number")
    elif daily_change_threshold.isalpha():
        st.text("Please type the threshold for the percentage change as a number")
    elif pct_volume_breakout.isalpha():
        st.text("Please type the percentage volume breakout as a number")
    else:
        df = get_strategy(ticker, int(pct_volume_breakout), int(daily_change_threshold), int(holding_period), rolling_window, start_date, end_date)
        buy_day_stats = create_buy_day_stats(df)
        pnl = crete_pnl_df(buy_day_stats, df)
        
        fig = go.Figure(data=[go.Candlestick(x=df.index,
                open=df['open price'],
                high=df['high price'],
                low = df['low price'],
                close=df['close price'],
                increasing_line_color= '#636EFA')])
        fig.add_trace(go.Scatter(x = pnl[pnl['buy condition'] == True]['date'],
                                        y = pnl[pnl['buy condition'] == True]['buy price'],
                                        mode = 'markers',
                                        marker=dict(
                                            color='green', 
                                            size=12, 
                                            symbol='arrow'
                                        ),
                                        name = 'buy date'))
        fig.add_trace(go.Scatter(x = pnl[pnl['sell'] == True]['date'],
                                        y = pnl[pnl['sell'] == True]['sell price'],
                                        mode = 'markers',
                                        marker=dict(
                                            color='red', 
                                            size=12, 
                                            symbol='arrow',
                                            angle=180
                                        ),
                                        name = 'sell date'))
        fig.update_layout(
            title=f'{ticker} price from {start_date} to {end_date} with buy date and sell date marker',
            yaxis_title='Daily Price',
            height = 500)
        st.plotly_chart(fig, use_container_width=True)

        plotly_fig = px.line(pnl, 
                    x ='date',
                    y=['pct change'],
                    title=f"Percentage PnL over time with the current strategy")
        plotly_fig.add_trace(go.Scatter(x = pnl[pnl['buy condition'] == True]['date'],
                                        y = pnl[pnl['buy condition'] == True]['pct change'],
                                        mode = 'markers',
                                        marker=dict(
                                            color='green', 
                                            size=10, 
                                            symbol='arrow'
                                        ),
                                        name = 'buy date'))
        plotly_fig.add_trace(go.Scatter(x = pnl[pnl['sell'] == True]['date'],
                                        y = pnl[pnl['sell'] == True]['pct change'],
                                        mode = 'markers',
                                        marker=dict(
                                            color='red', 
                                            size=10, 
                                            symbol='arrow',
                                            angle=180
                                        ),
                                        name = 'sell date'))

        st.plotly_chart(plotly_fig, use_container_width=True)

        
        st.write(f"With this strategy, there are {len(buy_day_stats)} days in total that we are going to buy and sell the stocks.")
        if len(buy_day_stats) > 0:
            
            st.write(f"The accumulative profit is {buy_day_stats['accumulative pnl'].iloc[-1]:.4f}% as of {end_date}")
            st.download_button(label="Click here to download the breakdown result as csv",
                            data=format_df_before_download(buy_day_stats, rolling_window).to_csv().encode("utf-8"),
                            file_name=f"{ticker}_buy_day_breakdown.csv",
                            mime="text/csv")
        
            