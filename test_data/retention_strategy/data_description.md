# Data Profile: Telco Customer Churn

## Overview
The dataset includes information about a fictional telco company that provided home phone and Internet services to 7043 customers in California in Q3. It indicates which customers have left, stayed, or signed up for their service.

## File Structure
- **Format**: CSV
- **Rows**: 7043
- **Target Variable**: `Churn`

## Columns Description

### Customer Demographics
- `customerID`: Unique ID for each customer.
- `gender`: Whether the customer is a male or a female.
- `SeniorCitizen`: Whether the customer is a senior citizen (1, 0).
- `Partner`: Whether the customer has a partner (Yes, No).
- `Dependents`: Whether the customer has dependents (Yes, No).

### Service Information
- `PhoneService`: Whether the customer has a phone service (Yes, No).
- `MultipleLines`: Whether the customer has multiple lines (Yes, No, No phone service).
- `InternetService`: Customer’s internet service provider (DSL, Fiber optic, No).
- `OnlineSecurity`: Whether the customer has online security (Yes, No, No internet service).
- `OnlineBackup`: Whether the customer has online backup.
- `DeviceProtection`: Whether the customer has device protection.
- `TechSupport`: Whether the customer has tech support.
- `StreamingTV`: Whether the customer has streaming TV.
- `StreamingMovies`: Whether the customer has streaming movies.

### Account Information
- `Tenure`: Number of months the customer has stayed with the company.
- `Contract`: The contract term of the customer (Month-to-month, One year, Two year).
- `PaperlessBilling`: Whether the customer has paperless billing (Yes, No).
- `PaymentMethod`: The customer’s payment method (Electronic check, Mailed check, Bank transfer (automatic), Credit card (automatic)).
- `MonthlyCharges`: The amount charged to the customer monthly.
- `TotalCharges`: The total amount charged to the customer.

### Target
- `Churn`: Whether the customer churned (Yes or No).