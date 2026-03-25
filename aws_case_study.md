# CASE STUDY: DriftWatch — Real-Time ML Observability on AWS

## 1. Project Overview (The "Why")
In traditional software, if a bug happens, the app crashes. In Machine Learning (ML), the app stays "UP" but the results become **WRONG**. This is called **Model Drift**. 

**DriftWatch** is a monitoring platform that detects when the data entering a model (Serving Data) starts moving away from the data used during training (Reference Data). It uses statistical tests like **PSI (Population Stability Index)** and **KL-Divergence** to catch these shifts before they impact business decisions.

---

## 2. Positioning in the ML Pipeline
This project sits in the **"Model Monitoring & Observability"** stage of the ML Lifecycle.

1.  **Training**: (Before DriftWatch) — Data scientists build a model.
2.  **Inference**: (Live) — The model makes predictions.
3.  **Observability (DriftWatch)**: Ensures the data quality remains high.
4.  **Feedback Loop**: Alerts the team to "Retrain" the model if drift is high.

---

## 3. AWS Architecture (The "How")

### A. Compute: Amazon EC2 (The Brain)
*   **Service**: EC2 (`t3.micro`) running Ubuntu and Docker.
*   **Role**: It hosts the **Python FastAPI backend** and the **React frontend**. 
*   **Why AWS?**: We chose EC2 because ML libraries (Pandas, SciPy, Scikit-learn) are too large for serverless functions (Lambda). EC2 provides a persistent environment to run heavy statistical calculations in real-time.

### B. Storage: Amazon S3 (The Data Lake)
*   **Service**: Amazon S3 (Simple Storage Service).
*   **Role**: To store **Training Fingerprints** and **Historical Reports**.
*   **Why AWS?**: In Data Engineering, S3 acts as a "Durable Storage Layer." Even if our server crashes, our historical drift data is safe and versioned in S3.

### C. Database: Amazon RDS (Metadata & Audit)
*   **Service**: Relational Database Service (PostgreSQL).
*   **Role**: Stores the metadata for every drift check (Timestamp, Severity, Feature Counts).
*   **Why AWS?**: RDS handles automatic backups and scaling. It allows us to perform SQL queries to find "Drift Trends" over time without slowing down the main analysis engine.

### D. Alerts: Amazon SNS (Event Notification)
*   **Service**: Simple Notification Service.
*   **Role**: To send **Real-Time Email Alerts** to the engineering team.
*   **Why AWS?**: It decouples the "Detection" from the "Notification." If the backend detects a "CRITICAL" drift, it publishes a message to an SNS Topic; SNS then handles the delivery to one or many subscribers (Email/SMS).

---

## 4. The Data Engineering Workflow
1.  **Ingestion**: User uploads Serving Data via the React Dashboard.
2.  **Processing**: The EC2 backend runs a statistical comparison against the Training data.
3.  **Persistence**:
    *   The **Raw JSON Report** is synced to **S3**.
    *   The **Metadata Summary** is saved to **RDS**.
4.  **Output & Alerting**: 
    *   The **Dashboard** displays visual charts.
    *   If drift is > 0.2 (Critical), **SNS** sends an automated email.

---

## 5. Summary for your Presentation
*"For my case study, I built a cloud-native ML Monitoring tool. I used **EC2** for computation, **RDS** for relational data tracking, and **S3** as a durable storage layer. By integrating **Amazon SNS**, I closed the 'Monitoring Loop' by automating alerts. This project demonstrates how AWS services work together to maintain 'Model Trust' in a production Data Engineering pipeline."*
