# dashboard.py
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database.db import get_session
from database.models import Product, PriceHistory, StockHistory
import datetime

# Create a Dash app
app = dash.Dash(__name__, routes_pathname_prefix='/dashboard/')
server = app.server  # for gunicorn deployment

# Layout
app.layout = html.Div([
    html.H1('RTX 5090 Stock Tracker Dashboard'),
    
    html.Div([
        html.Label('Select Product:'),
        dcc.Dropdown(
            id='product-dropdown',
            options=[],  # Will be populated in callback
            value=None
        ),
        
        html.Label('Select Time Range:'),
        dcc.RadioItems(
            id='time-range',
            options=[
                {'label': '7 Days', 'value': 7},
                {'label': '30 Days', 'value': 30},
                {'label': '90 Days', 'value': 90},
                {'label': 'All Time', 'value': 0}
            ],
            value=30,
            labelStyle={'display': 'inline-block', 'margin-right': '10px'}
        )
    ]),
    
    html.Div([
        dcc.Graph(id='price-history-graph'),
        dcc.Graph(id='stock-history-graph')
    ]),
    
    html.Div([
        html.H2('Price Statistics'),
        html.Div(id='price-stats')
    ])
])

# Callbacks
@app.callback(
    Output('product-dropdown', 'options'),
    Input('product-dropdown', 'search_value')
)
def update_product_options(search_value):
    session = get_session()
    products = session.query(Product).all()
    session.close()
    
    return [{'label': f"{p.name} ({p.manufacturer})", 'value': p.id} for p in products]

@app.callback(
    [Output('price-history-graph', 'figure'),
     Output('stock-history-graph', 'figure'),
     Output('price-stats', 'children')],
    [Input('product-dropdown', 'value'),
     Input('time-range', 'value')]
)
def update_graphs(product_id, days):
    if not product_id:
        return {}, {}, "Please select a product"
    
    session = get_session()
    product = session.query(Product).get(product_id)
    
    # Get date range
    end_date = datetime.datetime.utcnow()
    start_date = end_date - datetime.timedelta(days=days) if days > 0 else datetime.datetime.min
    
    # Get price history
    price_history = session.query(PriceHistory)\
        .filter(PriceHistory.product_id == product_id)\
        .filter(PriceHistory.timestamp >= start_date)\
        .order_by(PriceHistory.timestamp).all()
    
    # Get stock history
    stock_history = session.query(StockHistory)\
        .filter(StockHistory.product_id == product_id)\
        .filter(StockHistory.timestamp >= start_date)\
        .order_by(StockHistory.timestamp).all()
    
    session.close()
    
    # Create price history figure
    price_fig = go.Figure()
    
    if price_history:
        dates = [ph.timestamp for ph in price_history]
        prices = [ph.price for ph in price_history]
        
        price_fig.add_trace(go.Scatter(
            x=dates, 
            y=prices,
            mode='lines+markers',
            name='Price History',
            line=dict(color='#1f77b4', width=2)
        ))
        
        price_fig.update_layout(
            title=f"Price History for {product.name}",
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            template="plotly_white"
        )
    else:
        price_fig.update_layout(
            title="No price history data available"
        )
    
    # Create stock history figure
    stock_fig = go.Figure()
    
    if stock_history:
        dates = [sh.timestamp for sh in stock_history]
        stocks = [1 if sh.in_stock else 0 for sh in stock_history]
        
        stock_fig.add_trace(go.Scatter(
            x=dates,
            y=stocks,
            mode='lines',
            name='Stock Status',
            line=dict(shape='hv', color='#2ca02c', width=2)
        ))
        
        stock_fig.add_trace(go.Scatter(
            x=dates,
            y=stocks,
            mode='none',
            fill='tozeroy',
            fillcolor='rgba(44, 160, 44, 0.3)',
            showlegend=False
        ))
        
        stock_fig.update_layout(
            title=f"Stock History for {product.name}",
            xaxis_title="Date",
            yaxis_title="In Stock",
            template="plotly_white"
        )
        
        stock_fig.update_yaxes(
            tickvals=[0, 1],
            ticktext=["Out of Stock", "In Stock"]
        )
    else:
        stock_fig.update_layout(
            title="No stock history data available"
        )
    
    # Calculate price statistics
    if price_history:
        prices = [ph.price for ph in price_history]
        current_price = prices[-1] if prices else None
        min_price = min(prices) if prices else None
        max_price = max(prices) if prices else None
        avg_price = sum(prices) / len(prices) if prices else None
        
        stats = html.Div([
            html.Table([
                html.Tr([html.Td("Current Price:"), html.Td(f"${current_price:.2f}" if current_price else "N/A")]),
                html.Tr([html.Td("Minimum Price:"), html.Td(f"${min_price:.2f}" if min_price else "N/A")]),
                html.Tr([html.Td("Maximum Price:"), html.Td(f"${max_price:.2f}" if max_price else "N/A")]),
                html.Tr([html.Td("Average Price:"), html.Td(f"${avg_price:.2f}" if avg_price else "N/A")])
            ], className="table table-striped")
        ])
    else:
        stats = "No price data available"
    
    return price_fig, stock_fig, stats

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
