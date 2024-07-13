import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from email.message import EmailMessage
import smtplib
from bs4 import BeautifulSoup
import time
from sqlalchemy import create_engine, Column, Integer, String, Float, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import logging
import schedule
from circuitbreaker import circuit

# Set up logging
logging.basicConfig(filename='scraper.log', level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database credentials from environment variables
DB_USERNAME = os.environ.get('DB_USERNAME', 'pxhane')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_HOST = os.environ.get('DB_HOST', 'localhost')
DB_NAME = os.environ.get('DB_NAME', 'pxhane')

# Database configuration
DATABASE_URL = f"postgresql://{DB_USERNAME}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# The ORM model
class Property(Base):
    __tablename__ = 'properties'

    id = Column(Integer, primary_key=True)
    property_type = Column(String)
    volume_no = Column(String)
    property_description = Column(String)
    street_address = Column(String)
    extent = Column(Float)
    market_value = Column(Float)
    date_scraped = Column(Date)

Base.metadata.create_all(engine)


# Retry configuration
retry_strategy = Retry(
    total=3,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
    backoff_factor=1
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

# Alert function
def send_alert(subject, message):
    msg = EmailMessage()
    msg.set_content(message)
    msg['Subject'] = subject
    msg['From'] = "alerts@example.com"
    msg['To'] = "admin@example.com"

    try:
        with smtplib.SMTP('smtp.example.com', 587) as server:
            server.starttls()
            server.login("alerts@example.com", "password")
            server.send_message(msg)
        logger.info("Alert sent successfully")
    except Exception as e:
        logger.error(f"Failed to send alert: {str(e)}")

# Scraping function
def scrape_data(property_type, volume_no):
    url = "https://valuation2017.durban.gov.za/"
    
    try:
        response = requests.post(url, data={
            "property_type": property_type,
            "volume_no": volume_no
        }, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract data from the soup object
        properties = []
        for property_element in soup.find_all('div', class_='property'):
            property_data = {
                'property_type': property_type,
                'volume_no': volume_no,
                'property_description': property_element.find('span', class_='description').text,
                'street_address': property_element.find('span', class_='address').text,
                'extent': float(property_element.find('span', class_='extent').text),
                'market_value': float(property_element.find('span', class_='value').text),
            }
            properties.append(property_data)
        
        return properties
    except requests.RequestException as e:
        logger.error(f"Error scraping data: {str(e)}")
        send_alert("Scraping Error", f"Failed to scrape data for {property_type}, Volume {volume_no}: {str(e)}")
        return None

# Data cleaning function
def clean_data(properties):
    cleaned_properties = []
    for prop in properties:
        # removing whitespace and standardizing formats.
        cleaned_prop = {
            'property_type': prop['property_type'].strip(),
            'volume_no': prop['volume_no'].strip(),
            'property_description': prop['property_description'].strip(),
            'street_address': prop['street_address'].strip(),
            'extent': round(prop['extent'], 2),
            'market_value': round(prop['market_value'], 2),
        }
        cleaned_properties.append(cleaned_prop)
    return cleaned_properties

# Storing data
def store_data(properties):
    session = Session()
    try:
        for prop in properties:
            new_property = Property(
                property_type=prop['property_type'],
                volume_no=prop['volume_no'],
                property_description=prop['property_description'],
                street_address=prop['street_address'],
                extent=prop['extent'],
                market_value=prop['market_value'],
                date_scraped=datetime.now().date()
            )
            session.add(new_property)
        session.commit()
        logger.info(f"Successfully stored {len(properties)} properties")
    except Exception as e:
        session.rollback()
        logger.error(f"Error storing data: {str(e)}")
    finally:
        session.close()

# Scraping data
@circuit(failure_threshold=5, recovery_timeout=60)
def run_scraper():
    property_types = ['Full Title Property', 'Sectional Title Property']
    volume_nos = range(1, 90) 
    
    for property_type in property_types:
        for volume_no in volume_nos:
            properties = scrape_data(property_type, volume_no)
            if properties:
                cleaned_properties = clean_data(properties)
                store_data(cleaned_properties)
            time.sleep(5)  # delay a bit to avoid overwhelming the server

def scheduled_job():
    try:
        run_scraper()
    except Exception as e:
        logger.error(f"Scheduled job failed: {str(e)}")
        send_alert("Scheduled Job Failed", f"The daily scraping job failed: {str(e)}")

# Schedule the scraper to run daily at 2am
schedule.every().day.at("02:00").do(scheduled_job)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(60)