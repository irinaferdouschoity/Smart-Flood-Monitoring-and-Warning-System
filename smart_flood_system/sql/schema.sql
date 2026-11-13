CREATE DATABASE IF NOT EXISTS smart_flood_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE smart_flood_system;
CREATE TABLE IF NOT EXISTS locations (
 location_id INT AUTO_INCREMENT PRIMARY KEY,
 location_name VARCHAR(150) NOT NULL,
 country VARCHAR(100) NOT NULL,
 latitude DECIMAL(9,6) NOT NULL,
 longitude DECIMAL(9,6) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 UNIQUE KEY uq_location (location_name,country,latitude,longitude), INDEX idx_coords(latitude,longitude)
);
CREATE TABLE IF NOT EXISTS weather_observations (
 observation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
 location_id INT NOT NULL,
 observation_date DATE NOT NULL,
 precipitation DECIMAL(12,4), temperature_avg DECIMAL(8,3), temperature_max DECIMAL(8,3), temperature_min DECIMAL(8,3), humidity DECIMAL(8,3), dew_point DECIMAL(8,3), wind_speed DECIMAL(8,3), surface_pressure DECIMAL(10,3), data_source VARCHAR(80) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(location_id) REFERENCES locations(location_id) ON DELETE CASCADE,
 UNIQUE KEY uq_weather(location_id,observation_date,data_source), INDEX idx_weather(location_id,observation_date)
);
CREATE TABLE IF NOT EXISTS satellite_precipitation (
 id BIGINT AUTO_INCREMENT PRIMARY KEY,
 location_id INT NOT NULL,
 observation_time DATETIME NOT NULL,
 precipitation DECIMAL(12,4), latitude DECIMAL(9,6) NOT NULL, longitude DECIMAL(9,6) NOT NULL, dataset VARCHAR(120) NOT NULL, data_source VARCHAR(80) NOT NULL, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(location_id) REFERENCES locations(location_id) ON DELETE CASCADE,
 UNIQUE KEY uq_sat(location_id,observation_time,dataset), INDEX idx_sat(location_id,observation_time)
);
CREATE TABLE IF NOT EXISTS flood_events (
 flood_event_id BIGINT AUTO_INCREMENT PRIMARY KEY,
 location_id INT NOT NULL,
 event_date DATE NOT NULL,
 flood_occurred TINYINT(1) NOT NULL,
 severity VARCHAR(30), affected_area DECIMAL(15,3), source VARCHAR(255), description TEXT, created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(location_id) REFERENCES locations(location_id) ON DELETE CASCADE,
 UNIQUE KEY uq_flood(location_id,event_date,source), INDEX idx_flood(location_id,event_date)
);
CREATE TABLE IF NOT EXISTS flood_predictions (
 prediction_id BIGINT AUTO_INCREMENT PRIMARY KEY,
 location_id INT NOT NULL,
 prediction_time DATETIME NOT NULL,
 flood_probability DECIMAL(8,6) NOT NULL,
 risk_level VARCHAR(20) NOT NULL,
 model_version VARCHAR(100) NOT NULL,
 created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(location_id) REFERENCES locations(location_id) ON DELETE CASCADE,
 INDEX idx_prediction(location_id,prediction_time)
);
CREATE TABLE IF NOT EXISTS model_runs (
 model_run_id BIGINT AUTO_INCREMENT PRIMARY KEY,
 model_name VARCHAR(100) NOT NULL,
 training_date DATETIME NOT NULL,
 dataset_size INT NOT NULL,
 accuracy DECIMAL(10,6), precision_score DECIMAL(10,6), recall_score DECIMAL(10,6), f1_score DECIMAL(10,6), roc_auc DECIMAL(10,6), model_file VARCHAR(255), notes TEXT
);
