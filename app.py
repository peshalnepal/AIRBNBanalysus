import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for Matplotlib
from flask import Flask, render_template
import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import io
import base64
import configparser
from sqlalchemy import create_engine

app = Flask(__name__)


# Read from the config file
config = configparser.ConfigParser()
config.read('./config/dfconfig.config')

# Fetch database connection parameters
rds_host = config.get('database', 'rds_host')
rds_user = config.get('database', 'rds_user')
rds_password = config.get('database', 'rds_password')
rds_database = config.get('database', 'rds_database')


def fetch_data_from_rds():
    """Fetch data from the RDS database table and return a DataFrame."""
    engine = create_engine(f'mysql+pymysql://{rds_user}:{rds_password}@{rds_host}/{rds_database}')
    query = "SELECT * FROM AB_NYC"
    return pd.read_sql(query, con=engine)


# Load and clean the dataset
def cleaning_dataset(df):
    """Cleans the dataset by removing duplicates, outliers, and invalid data."""
    df.drop_duplicates(subset=['id'], inplace=True)
    Q1 = df['price'].quantile(0.25)
    Q3 = df['price'].quantile(0.75)
    IQR = Q3 - Q1
    df = df[(df['price'] >= Q1 - 1.5 * IQR) & (df['price'] <= Q3 + 1.5 * IQR)]
    df = df[(df['availability_365'] >= 0) & (df['availability_365'] <= 365)]
    df = df[(df['minimum_nights'] > 0) & (df['minimum_nights'] < 365)]
    df = df[(df['latitude'] >= 40) & (df['latitude'] <= 41)]
    df = df[(df['longitude'] >= -75) & (df['longitude'] <= -73)]
    df['name'] = df['name'].str.replace(r'[^\w\s]', '', regex=True).str.title()
    df['host_name'] = df['host_name'].str.title()
    return df

# Load the dataset and clean it
df = fetch_data_from_rds()
df = cleaning_dataset(df)

@app.route('/')
def home():
    """Renders the main page with chart descriptions."""
    chart_descriptions = [
        {
            "url": "/chart_boxplot",
            "description": "Entire homes/apartments and private rooms receive more reviews per month compared to shared rooms, with outliers indicating some listings are highly reviewed."
        },
        {
            "url": "/bar_graph",
            "description": "Private rooms and entire apartments dominate listings in Brooklyn and Manhattan, with shared rooms being relatively rare across all neighborhoods."
        },
        {
            "url": "/chart_map",
            "description": "The map shows that Airbnb prices are concentrated in Manhattan and parts of Brooklyn, with higher prices in central neighborhoods."
        },
        {
            "url": "/scatter_plot",
            "description": "Room prices vary significantly, but most highly available listings are either private rooms or entire apartments."
        },
    ]
    return render_template("index.html", charts=chart_descriptions)


@app.route('/chart_boxplot')
def chart_boxplot():
    """Creates and returns a box plot of reviews per month by room type."""
    fig, ax = plt.subplots(figsize=(10, 6))
    df[['room_type', 'reviews_per_month']].boxplot(
        by='room_type', column='reviews_per_month', grid=False, ax=ax
    )
    ax.set_title("Distribution of Reviews per Month by Room Type")
    ax.set_xlabel("Room Type")
    ax.set_ylabel("Reviews per Month")
    ax.grid(False)

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    plot_url = base64.b64encode(img.getvalue()).decode()
    return f'<img src="data:image/png;base64,{plot_url}" style="width:100%; height:100%;" />'

@app.route('/bar_graph')
def bar_graph():
    """Creates and returns a bar graph of the most common room types in each neighborhood."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Create a pivot table
    room_type_counts = df.pivot_table(
        index="neighbourhood_group",
        columns="room_type",
        values="id",
        aggfunc="count",
        fill_value=0
    )

    # Plot a stacked bar chart
    room_type_counts.plot(
        kind="bar",
        stacked=False,
        colormap="viridis",
        ax=ax
    )

    # Add labels and title
    ax.set_title("Most Common Room Types in Each Neighborhood", fontsize=16)
    ax.set_xlabel("Neighborhood", fontsize=12)
    ax.set_ylabel("Number of Listings", fontsize=12)
    ax.legend(title="Room Type", fontsize=10)
    ax.grid(axis="y", alpha=0.5)


    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    plot_url = base64.b64encode(img.getvalue()).decode()
    return f'<img src="data:image/png;base64,{plot_url}" style="width:100%; height:100%;" />'

@app.route('/scatter_plot')
def scatter_plot():
    """Creates and returns a scatter plot of price vs. availability by room type with distinct colors."""
    # Dynamically generate distinct colors for each room type
    room_type_colors = {
        "Entire home/apt": [0.1, 0.6, 0.8],  # Light blue
        "Private room": [0.8, 0.1, 0.2],  # Red
        "Shared room": [0.2, 0.8, 0.1],  # Green
        "Hotel room": [0.9, 0.8, 0.2]  # Yellow
    }

    # Create the scatter plot
    plt.figure(figsize=(10, 6))
    for room_type, color in room_type_colors.items():
        subset = df[df["room_type"] == room_type]
        plt.scatter(
            subset["price"],
            subset["availability_365"],
            color=[color],  # Use the color keyword argument
            label=room_type,
            alpha=0.7
        )

    # Add labels, legend, and title
    plt.xlabel("Price", fontsize=12)
    plt.ylabel("Availability (365 Days)", fontsize=12)
    plt.title("Scatter Plot of Price vs. Availability by Room Type", fontsize=14)
    plt.legend(title="Room Type", fontsize=10, loc='upper right')
    plt.grid(alpha=0.5)

    # Save the plot to a BytesIO object
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plt.close()
    plot_url = base64.b64encode(img.getvalue()).decode()
    return f'<img src="data:image/png;base64,{plot_url}" style="width:100%; height:100%;" />'



@app.route('/chart_map')
def chart_map():
    """Creates and returns a map visualization of average prices by neighborhood."""
    average_price_df = df.groupby(["neighbourhood", "neighbourhood_group"]).agg(
        {"latitude": "mean", "longitude": "mean", "price": "mean"}
    ).reset_index()

    fig = px.scatter_mapbox(
        average_price_df,
        lat="latitude",
        lon="longitude",
        size="price",
        color="price",
        color_continuous_scale="Viridis",
        hover_name="neighbourhood",
        hover_data={"price": True, "neighbourhood_group": True},
        title="Average Airbnb Prices by Neighborhood",
        zoom=9,
        width=480,
        height=380,
    )

    # Adjust the size scaling
    fig.update_traces(
        marker=dict(
            sizemode="area",  # Adjust the size based on the area
            sizeref=2.*max(average_price_df['price'])/(15**2),  # Increased scaling to make points smaller
            sizemin=2,  # Ensure a minimum point size
        )
    )


    fig.update_layout(mapbox_style="carto-positron", margin={"r": 0, "t": 40, "l": 0, "b": 0})
    return fig.to_html(full_html=False)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
