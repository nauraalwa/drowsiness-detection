import streamlit as st
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import csv
import os

def Hourly():
    # Initialize session state for hour list if it doesn't exist
    if "hour" not in st.session_state:
        st.session_state.hour = []
    

    Chart, Table = st.tabs(["Live Chart", "Data Table"])

    with Chart:
        # Prepare data for plotting
        if st.session_state.hour:
            x = [entry[0] for entry in st.session_state.hour]
            y = [entry[1] for entry in st.session_state.hour]
            
            # Create dynamic plot
            fig, ax = plt.subplots(figsize=(10, 4))
            
            # Color points based on drowsiness level (green to red)
            colors = plt.cm.RdYlGn_r(np.linspace(0, 1, len(y)))
            scatter = ax.scatter(x, y, c=y, cmap='RdYlGn_r', vmin=1, vmax=10, s=100)
            
            # Add line connecting points
            ax.plot(x, y, 'b--', alpha=0.3)
            
            # Style the plot
            ax.set_xlim(0, 60)
            ax.set_xlabel("Time (minutes)")
            ax.set_ylabel("Drowsiness Level")
            ax.set_title("Drowsiness Monitoring - Live Feed")
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # Add colorbar
            cbar = plt.colorbar(scatter)
            cbar.set_label('Drowsiness Scale')
            
            st.pyplot(fig)

    with Table:
        if st.session_state.hour:
            display = []
            for i in st.session_state.hour:
                minutes = int(i[1])
                seconds = int((i[1] - int(i[1])) * 60)
                time = f"{minutes}:{seconds}"
                display.append([i[0], time])
            data = pd.DataFrame(display, columns=["Drowsiness", "Time"])
            st.dataframe(data)
        else:
            st.write("No inputs yet.")

def Weekly():
    if "week" not in st.session_state:
        st.session_state.week = []
        # will be in the form: [value, day of the week, time of week, week number]

    file_path = os.path.join(os.getcwd(), "./weekly_data.csv")
    
    # Check if the file exists; if not, create it with the header
    if not os.path.exists(file_path):
        with open(file_path, mode="w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Drowsiness", "Day", "Hour", "Week"])

# Button to add the input to the session state list

    # Button to load and display data from the CSV file
    if st.button("Generate"):
        st.session_state.week = []
        # Read the data from the CSV and append it to the session state
        with open(file_path, mode="r", newline='') as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            for row in reader:
                try:
                    # Convert data to appropriate types
                    drowsiness = float(row[0])
                    day = row[1]
                    hour = int(row[2])
                    week = row[3]
                    st.session_state.week.append([drowsiness, day, hour, week])
                except ValueError:
                    st.error("Error in data format in CSV file.")

        # Graph time
    if st.session_state.week:
        # Create a DataFrame from the session state
        data = pd.DataFrame(st.session_state.week, columns=["Drowsiness", "Day", "Hour", "Week"])
        data["Drowsiness"] = data["Drowsiness"].astype(float)
        data["Hour"] = data["Hour"].astype(int)
        data["Day"] = data["Day"].str.title()  # Ensure the days are capitalized correctly

        # Pivot data for the heatmap (Average drowsiness per hour per day)
        weekly = data.pivot_table(values="Drowsiness", index="Hour", columns="Day", aggfunc="mean")
        
        # Define the correct order of days of the week
        order = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
        existing_days = [day for day in order if day in weekly.columns]
        
        # Reorder the columns to match the days present in the data
        weekly = weekly[existing_days]

        # Plot the heatmap
        fig, ax = plt.subplots(figsize=(10, 6))
        sns.heatmap(weekly, annot=True, fmt=".1f", cmap="YlOrRd", cbar_kws={"label": "Drowsiness Level"}, ax=ax, linewidth=.5)
        ax.set_yticks(range(0, 24))
        ax.set_yticklabels(i for i in range(24))
        ax.set_title("Sleepiness of the Week")
        ax.set_xlabel("Day of the Week")
        ax.set_xticks(range(0, 7))
        ax.set_ylabel("Hours")
        ax.set_xticklabels(order, rotation=45, ha="right")
        plt.tight_layout()
        st.pyplot(fig)

# Main app layout
st.title("Drowsiness Monitor")

# Different graphs to choose from
graph = st.radio(
    "Select view:",
    ("Hourly Drowsiness", "Weekly Drowsiness"),
    horizontal=True
)

if graph == "Hourly Drowsiness":
    Hourly()
elif graph == "Weekly Drowsiness":
    Weekly()
