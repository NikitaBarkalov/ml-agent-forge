# Data Profile: Ames Housing Data

## Overview
This dataset describes the sale of individual residential property in Ames, Iowa from 2006 to 2010. It contains a large number of explanatory variables (79) involved in assessing home values.

## File Structure
- **Format**: CSV
- **Rows**: 1460
- **Target Variable**: `SalePrice`

## Key Columns Description (Selected)

| Column | Description |
|--------|-------------|
| **SalePrice** | The property's sale price in dollars. This is the target variable. |
| **MSSubClass** | The building class. |
| **MSZoning** | The general zoning classification. |
| **LotFrontage** | Linear feet of street connected to property. |
| **LotArea** | Lot size in square feet. |
| **Neighborhood** | Physical locations within Ames city limits. |
| **OverallQual** | Overall material and finish quality (1-10). |
| **OverallCond** | Overall condition rating (1-10). |
| **YearBuilt** | Original construction date. |
| **GrLivArea** | Above grade (ground) living area square feet. |
| **FullBath** | Full bathrooms above grade. |
| **BedroomAbvGr** | Number of bedrooms above basement level. |
| **KitchenQual** | Kitchen quality. |
| **GarageCars** | Size of garage in car capacity. |
| **GarageArea** | Size of garage in square feet. |

## Notes
- There are many categorical variables (e.g., `KitchenQual`: Ex, Gd, TA, Fa, Po).
- Some columns like `PoolQC`, `Fence` have many missing values which imply the absence of the feature.