import pandas as pd
import os
from sqlalchemy import create_engine # Import the create_engine function from SQLAlchemy
import logging
import time 

logging.basicConfig(
    filename="logs/ingestion_db.log",
    level = logging.DEBUG,
    format = "%(asctime)s - %(levelname)s - %(message)s",
    filemode="a"
)

# Create a connection (engine) to the SQLite database file named 'inventory.db'
# This will allow us to run SQL queries and interact with the database
engine = create_engine('sqlite:///inventory.db')

def ingest_db(df,table_name,engine):
    '''this function will ingest the dataframe into database table'''
    df.to_sql(table_name,con=engine,if_exists = 'replace', index=False)
def load_raw_data(): 
    '''this function will the load the CSVs as datfraame and ingest into db'''
    start = time.time()
    for file in os.listdir('data'):
        if '.csv' in file: # Only read csv file
            df = pd.read_csv('data/'+file)
            logging.info(f'Ingesting {file} in db')
            ingest_db(df,file[:-4],engine)
    end = time.time()
    total_time = (end - start) / 60
    logging.info('----------Ingestion Complete------------')
    logging.info(f'Total time taken: {total_time} minutes')

if __name__ == '__main__':
    load_raw_data()
