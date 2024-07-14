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

HTML_PARSER = "html.parser"

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

# Alert function - for illustration: update emails and set pwd local env for this to work
def send_alert(subject, message):
    msg = EmailMessage()
    msg.set_content(message)
    msg['Subject'] = subject
    msg['From'] = "alerts@gmail.com"
    msg['To'] = "admin@gamil.com"

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login("alerts@gmail.com", os.environ.get('GMAIL_PASSWORD'))
            server.send_message(msg)
        logger.info("Alert sent successfully")
    except Exception as e:
        logger.error(f"Failed to send alert: {str(e)}")

# Scrape data
def scrape_data(property_type, volume_no):
    url = "https://valuation2017.durban.gov.za/FramePages/SearchType.aspx"
    
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, HTML_PARSER)
        
        # Find the dropdown list with id='drpSearchType' and select the desired property type
        dropdown = soup.find('select', {'id': 'drpSearchType'})
        if dropdown is None:
            logger.error("Dropdown element not found")
            return None
        
        for option in dropdown.find_all('option'):
            if option.text.strip() == property_type:
                option.select(property_type)
                break
        
        # Click on the 'Go' button with id='btnGo'
        go_button = soup.find('input', {'id': 'btnGo'})
        response = requests.post(url, data={'__EVENTTARGET': go_button['id']}, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, HTML_PARSER)
        
        # Find the 'Volume No.'
        dropdown = soup.find('select', {'id': 'drpVolumeNo'})
        if dropdown is None:
            logger.error("Dropdown element not found")
            return None
        
        for option in dropdown.find_all('option'):
            if option.text.strip() == volume_no:
                option.select(volume_no)
                break
        
        # Click on the 'Search' button
        search_button = soup.find('input', {'id': 'btnSearch'})
        response = requests.post(url, data={'__EVENTTARGET': search_button['id']}, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, HTML_PARSER)
        
        # Extract data from the search results table
        properties = []
        table = soup.find('table', {'class': 'searchResultTable'})
        for row in table.find_all('tr')[1:]:  # Skip the header row
            cells = row.find_all('td')
            property_data = {
                'property_type': property_type,
                'volume_no': volume_no,
                'property_description': cells[1].text.strip(),
                'street_address': cells[2].text.strip(),
                'extent': float(cells[5].text.strip()),
                'market_value': float(cells[6].text.strip()),
            }
            properties.append(property_data)
        
        return properties
    except requests.RequestException as e:
        logger.error(f"Error scraping data: {str(e)}")
        send_alert("Scraping Error", f"Failed to scrape data for {property_type}, Volume {volume_no}: {str(e)}")
        return None

# Clean data
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

# Store data
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
    #print(scrape_data('Full Title Property', '1'))  # For testing, uncomment this line
    scheduled_job()
    while True:
        schedule.run_pending()
        time.sleep(60)