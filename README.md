# Property Valuation Scraper and API

This project consists of a web scraper for property valuation data and a FastAPI-based API to query the scraped data saved to a PostgreSQL. The data is based from the Ethekwini Municipality 2017 data.

## Table of Contents

1. [Installation](#installation)
2. [Database Setup](#database-setup)
3. [Running the Application](#running-the-application)
4. [Testing the API](#testing-the-api)
5. [Deployment](#deployment)
   - [AWS Deployment](#aws-deployment)
   - [Robocorp Deployment](#robocorp-deployment)
6. [Additional Information](#additional-information)

## Installation

1. Clone the repository:
`git clone https://github.com/pebongue/scraper_property_valuation.git`
`cd scraper_property_valuation`

2. Create and activate a virtual environment:
`python -m venv venv`
`source venv/bin/activate`

3. Install the required packages: pip install -r requirements.txt

## Database Setup

1. Install PostgreSQL if you haven't already.

2. Create a new database: `createdb property_valuation`

3. Set up environment variables:
Create a `.env` file in the project root and add:
`export DB_USERNAME=your_username`
`export DB_PASSWORD=your_password`
`export DB_HOST=your_host`
`export DB_NAME=your_database_name`

## Running the Application

1. Start the FastAPI server: `uvicorn main:app --reload`

2. Run the scraper (in a separate terminal): `python3 scrap_properties.py`

## Testing the API

1. Open your browser and go to `http://localhost:8000/docs` to see the Swagger UI.

2. Use the interactive documentation to test the API endpoints.

3. To run unit tests: `pytest`

## Deployment

### AWS Deployment [Preferred deployment!]
We will use FastAPI running on AWS ECS, PostgrSQL, Docker, CloudWatch for monitoring, AWS Secrets Manager and some of the services listed below.

1. Set up an AWS account if you don't have one.

2. Install and configure the AWS CLI.

3. Create an ECR repository: `aws ecr create-repository --repository-name property-valuation-app`

4. Build and push the Docker image to ECS

5. Set up an ECS cluster, task definition, and services using AWS Console or CLI.

6. Configure the Application Load Balancer to route traffic to the ECS service, configure listener and target groups.

7. Set up a CI/CD pipeline using AWS CodePipeline and CodeBuild. [We can also use Github actions to deploy directly to AWS]

For detailed AWS deployment instructions, refer to the [AWS ECS documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/Welcome.html).

### Robocorp Deployment [Not included in the code - I left it out]
Robocorp is primarily focused on Robotic Process Automation (RPA) and we can use it to run the scraper as an automated process.

1. Sign up for a Robocorp account if you don't have one.

2. Install Robocorp CLI: `pip install rpaframework`

3. Initialize your Robocorp project: `rcc create`

4. Configure your `robot.yaml` and `conda.yaml` files as described in the project documentation.

5. Upload your bot to Robocorp Control Room: `rcc cloud push --workspace <your-workspace> --robot <your-robot-name>`

6. Set up a process in Robocorp Control Room and configure the schedule for daily runs.

For more details, refer to the [Robocorp documentation](https://robocorp.com/docs/).

## Additional Information

- The scraper is configured to run daily at 2am. Adjust the schedule in `scrap_properties.py`.
- The dependencies will be updated regularly.
- For production deployments, we will have monitoring and alert through AWS Cloudwatch.
- We will follow security best practices by using AWS Secrets Manager and AIM permissions, especially when dealing with sensitive data.
- I have implementated retry logic for HTTP requests, error logging, email alerts for critical errors, and a circuit breaker pattern to handle downtime.

For any issues or comments, please reach out to @pebongue.