# Data Profile: Online Retail Transaction Data

## Overview
This dataset contains all the transactions occurring between 01/12/2009 and 09/12/2011 for a UK-based and registered non-store online retail. The company mainly sells unique all-occasion gifts. Many customers of the company are wholesalers.

## File Structure
- **Format**: CSV / Excel
- **Rows**: ~500,000+ records
- **Granularity**: Each row represents a line item in a transaction (invoice).

## Columns Description

| Column Name   | Data Type | Description |
|---------------|-----------|-------------|
| **InvoiceNo** | String    | Invoice number. Nominal, a 6-digit integral number uniquely assigned to each transaction. If this code starts with letter 'c', it indicates a cancellation. |
| **StockCode** | String    | Product (item) code. Nominal, a 5-digit integral number uniquely assigned to each distinct product. |
| **Description**| String   | Product (item) name. Nominal. |
| **Quantity** | Integer   | The quantities of each product (item) per transaction. Numeric. |
| **InvoiceDate**| DateTime | Invice Date and time. Numeric, the day and time when each transaction was generated. |
| **UnitPrice** | Float     | Unit price. Numeric, Product price per unit in sterling. |
| **CustomerID**| String    | Customer number. Nominal, a 5-digit integral number uniquely assigned to each customer. |
| **Country** | String    | Country name. Nominal, the name of the country where each customer resides. |

## Notes for Analysis
- **Missing Values**: `CustomerID` may be missing for some guest checkouts.
- **Cancellations**: Transactions with negative `Quantity` usually represent returns or cancellations.
- **Outliers**: Watch out for test transactions (often manual entries with unusual stock codes).