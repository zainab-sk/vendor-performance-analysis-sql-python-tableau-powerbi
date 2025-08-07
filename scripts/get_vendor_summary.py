import sqlite3
import logging
import time 
from ingestion_db import ingest_db

logging.basicConfig(
    filename="logs/get_vendor_summary.log",
    level = logging.DEBUG,
    format = "%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)
def create_vendor_summary(conn):
    vendor_sales_summary = pd.read_sql_query("""
    -- First: calculate total freight costs per vendor
    WITH FreightSummary AS (
        SELECT 
            VendorNumber,                            -- Unique vendor ID
            SUM(Freight) as FreightCost              -- Total freight cost per vendor
        FROM Vendor_invoice
        GROUP BY VendorNumber
    ),

    -- Second: summarize purchase data for each vendor and brand
    PurchaseSummary AS (
        SELECT
            p.VendorNumber,                          -- Vendor ID
            p.VendorName,                            -- Vendor Name
            p.Brand,                                 -- Brand ID
            p.Description,                           -- Brand/product description
            p.PurchasePrice,                         -- Price at which it was bought
            pp.Volume,                               -- Volume in ml or litres
            pp.price as ActualPrice,                 -- Official price from price table
            SUM(p.Quantity) as TotalPurchaseQuantity,-- Total units purchased
            SUM(p.Dollars) as TotalPurchaseDollars   -- Total money spent on purchases
        FROM purchases p
        JOIN purchase_prices pp                      -- Join to get extra details like volume
            ON p.Brand = pp.Brand
        WHERE p.PurchasePrice > 0                    -- Ignore bad or zero-price records
        GROUP BY p.VendorNumber, p.VendorName, p.Brand
    ),

    -- Third: summarize sales data for each vendor and brand
    SalesSummary AS (
        SELECT
            VendorNo,                                -- Vendor ID from sales table
            Brand,                                   -- Brand ID
            SUM(SalesQuantity) as TotalSalesQuantity,  -- Total units sold
            SUM(SalesDollars) as TotalSalesDollars,    -- Total revenue
            SUM(SalesPrice) as TotalSalesPrice,        -- Aggregated sales price
            SUM(ExciseTax) as TotalExciseTax           -- Taxes collected
        FROM sales
        GROUP BY VendorNo, Brand
    )

    -- Final step: combine all the summaries
    SELECT 
        ps.VendorNumber,
        ps.VendorName,
        ps.Brand,
        ps.Description,
        ps.PurchasePrice,
        ps.ActualPrice,
        ps.Volume,
        ps.TotalPurchaseQuantity,
        ps.TotalPurchaseDollars,
        ss.TotalSalesQuantity,
        ss.TotalSalesDollars,
        ss.TotalSalesPrice,
        ss.TotalExciseTax,
        fs.FreightCost
    FROM PurchaseSummary ps 
    LEFT JOIN SalesSummary ss
        ON ps.VendorNumber = ss.VendorNo
        AND ps.Brand = ss.Brand
    LEFT JOIN FreightSummary fs
        ON ps.VendorNumber = fs.VendorNumber
    ORDER BY ps.TotalPurchaseDollars DESC -- Sort vendors by purchase volume
    """, conn)
    
    return vendor_sales_summary

def clean_data(df):
    '''this function will clean the data'''
    #changing data type to float
    df['Volume'] = df['Volume'].astype('float64')
    
    #filling missing values with 0
    df.fillna(0,inplace=True)
    
    #removing space from categorical columns
    df['VendorName'] = df['VendorName'].str.strip()
    df['Description'] = df['Description'].str.strip()
    
    # 1️⃣ Calculate Gross Profit for each vendor
    df['GrossProfit'] = df['TotalSalesDollars'] - df['TotalPurchaseDollars']
    # ➤ Gross Profit = Revenue from Sales - Cost of Purchases
    # ➤ Measures how much money the company makes after covering the cost of goods sold

    # 2️⃣ Calculate Profit Margin (%) for each vendor
    df['ProfitMargin'] = (df['GrossProfit'] / df['TotalSalesDollars']) * 100
    # ➤ Profit Margin (%) = (Gross Profit / Sales Revenue) * 100
    # ➤ Shows how much profit is generated per ₹100 of sales

    # 3️⃣ Calculate Stock Turnover Ratio
    df['StockTurnover'] = df['TotalSalesQuantity'] / df['TotalPurchaseQuantity']
    # ➤ Stock Turnover = Total Units Sold / Total Units Purchased
    # ➤ Indicates how efficiently inventory is being sold
    # ➤ A low ratio may indicate overstocking or weak sales

    # 4️⃣ Calculate Sales-to-Purchase Ratio
    df['SalestoPurchaseRatio'] = df['TotalSalesDollars'] / df['TotalPurchaseDollars']
    # ➤ Sales-to-Purchase Ratio = Total Sales Value / Total Purchase Value
    # ➤ Measures return on investment per vendor — how much revenue is generated for each rupee spent on inventory
    return df

if __name__ == '__main__':
    #creating database connection
    conn = sqlite3.connect ('inventory.db')
    
    logging.info( 'Creating Vendor Summary Table.....')
    summary_df = create_vendor_summary(conn)
    logging.info(summary_df.head())
    
    logging.info('Cleaning Data.....')
    clean_df = clean_data(summary_df)
    logging.info(clean_df.head())
    
    logging.info('Ingesting data.....')
    ingest_db(clean_df, 'vendor_sales_summary', conn)
    logging.info( 'Completed' )