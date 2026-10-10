**Smart Flood Monitoring and Warning System**

**About the Project**

Flooding is a major environmental challenge in many parts of the world. This project focuses on developing a Smart Flood Monitoring and Warning System that combines weather monitoring, data visualization, and machine learning-based flood risk estimation in one web application.

The system allows users to select a location and view available weather information, rainfall indicators, historical flood records, and estimated flood risk through a single dashboard.

The project explores how environmental data and machine learning can support flood monitoring in different geographical areas.

GitHub Repository: Smart Flood Monitoring and Warning System

**Features**

•	Location Selection: Select a monitored location from the dashboard.

•	Weather Monitoring: Display available rainfall, temperature, humidity, and other weather information.

•	Risk Map: View monitored locations on an interactive map.

•	Weather Graphs: Visualize rainfall, temperature, and humidity data.

•	Flood History: View available historical flood records.

•	Rainfall Indicator: Display a rainfall indicator based on historical rainfall information.

•	Machine Learning Prediction: Estimate flood risk and display the predicted risk level and probability.

•	Data Refresh: Request updates to the available monitoring data.

**Technologies Used**

•	Programming Language: Python

•	Backend Framework: FastAPI

•	Database: MySQL

•	Database Libraries: SQLAlchemy and PyMySQL

•	Frontend: HTML, CSS, and JavaScript

•	Data Visualization: Chart.js

•	Interactive Mapping: Leaflet

•	Machine Learning and Data Processing: Pandas and scikit-learn

•	Weather Data Source: NASA POWER

**Machine Learning Model**

The project includes a Random Forest model trained using a Haor flood-event dataset. The model uses 14 environmental and satellite-related features, including VV, VH, rainfall, soil moisture, temperature, wind, slope, TWI, and NDWI.

The model is integrated into the application through the backend API. Users can select a location on the dashboard and request a prediction using the available weather information.

The current implementation uses a Haor-trained model for experimental city-based prediction. Further evaluation is needed to determine how well the model performs in different geographical areas.

**Data Sources**

**NASA POWER**

NASA POWER daily weather data is used to provide weather information for the monitoring dashboard. Depending on data availability, the system can work with variables such as precipitation, temperature, humidity, wind speed, and surface pressure.

Source: NASA POWER

**Haor Flood Dataset**

The project uses a cleaned version of a Haor flood-event dataset for machine learning experiments.

•	Original Dataset: A SAR-verified flash flood event dataset for the haor wetlands of northeastern Bangladesh (2014–2024)

•	Authors: Salma Hoque Talukdar Koli and Fahima Haque Talukder Jely

•	Licence: Creative Commons Attribution 4.0 International (CC BY 4.0)

Modifications: The dataset was cleaned and prepared for machine learning experiments. The source, date, and event\_id columns were excluded from model predictors to reduce data leakage.

Please refer to the original dataset for its authoritative data, documentation, and attribution. Any redistributed modified dataset should retain appropriate attribution and comply with the applicable licence.

**MySQL Database**

The application uses MySQL to store and retrieve monitoring information, including location and weather records. A local MySQL database must be configured before running the application.

How to Run the Project

**Requirements**

Before running the project, make sure you have:

•	Python installed

•	MySQL and a local database server, such as XAMPP

•	The dependencies listed in requirements.txt

•	The required environment configuration

•	The trained model file required by the application

**1. Clone the Repository**

Clone the project from GitHub:

git clone https://github.com/irinaferdouschoity/Smart-Flood-Monitoring-and-Warning-System.git

cd Smart-Flood-Monitoring-and-Warning-System

**2. Create a Virtual Environment**

On Windows PowerShell, run:

python -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

**3. Install Dependencies**

Install the required Python packages:

pip install -r requirements.txt

**4. Configure the Database**

1\.	Start MySQL through XAMPP or another MySQL installation.

2\.	Create a database named smart\_flood\_system.

3\.	Configure the database connection using your local environment settings.

4\.	Copy .env.example to .env.

5\.	Enter your own database credentials and any other required configuration values in .env.

If a database schema is included in the repository, use it to create the required tables.

Important: Never upload your actual .env file, passwords, API credentials, or other secrets to GitHub.

**5. Start the Application**

The following command assumes main.py is in the repository's root directory, defines the FastAPI application as app, and has imports and file paths that work with the root-level layout.

python -m uvicorn main:app --reload

Keep the terminal running while using the application.

6\. Open the Application

•	Dashboard: http://127.0.0.1:8000/

•	API Documentation: http://127.0.0.1:8000/docs

**Project Status**

The dashboard, weather monitoring features, data visualization, and main prediction workflow have been implemented.

The project demonstrates an approach to combining environmental data, web technologies, and machine learning for flood monitoring.

Although the system is designed with applications in different geographical areas in mind, prediction performance depends on data availability, local environmental conditions, and appropriate model validation. The current city-based prediction workflow is experimental and should not be treated as a validated operational flood-warning service.





