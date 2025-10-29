<!-- Original Template: https://github.com/othneildrew/Best-README-Template/blob/main/BLANK_README.md#readme-top>
<a id="readme-top"></a>

<!-- PROJECT LOGO -->
<br />
<div align="center">
  <img src="static\images\data-extraction-automation-app-logo.png" alt="Logo" width="800" height="800">
  </a>

<h3 align="center">data-extraction-automation-app</h3>

  <p align="center">
    Internal webpage for data team to automate jira data requests, possibly expanded to serve as a customer data platform. 
  </p>
</div>

<!-- TABLE OF CONTENTS -->
<details>
  <summary style="font-size: 1.5em; font-weight: bold;">Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
      <ul>
        <li><a href="#built-with">Built With</a></li>
        <li><a href="#project-structure">Project Structure</a></li>
        <li><a href="#data-extraction-process-scenario">Data Extraction Process Scenario</a></li>
      </ul>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#prerequisites">Prerequisites</a></li>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#roadmap">Roadmap</a></li>
    <li><a href="#contact">Contact</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project
Objective: Project aims to automate data extraction process.

### Built With
* ![Python](https://img.shields.io/badge/python-3.12.10-blue) – Programming language  
* ![FastAPI](https://img.shields.io/badge/FastAPI-0.116.1-green) – Web framework for building APIs  
* ![Uvicorn](https://img.shields.io/badge/Uvicorn-0.35.0-orange) – ASGI server to run FastAPI  
* ![Jira](https://img.shields.io/badge/Jira--Python-3.10.5-0052CC) – Official Python client for interacting with Jira REST API  
* ![MySQL Connector](https://img.shields.io/badge/mysql--connector--python-8.1.0-yellow) – MySQL driver for database connectivity  
* ![Redis](https://img.shields.io/badge/Redis-6.4.0-red) – In-memory database for session management and caching  
* ![Requests](https://img.shields.io/badge/Requests-2.32.5-blue) – HTTP client for external API calls (e.g., Jira)  
* ![Pytest](https://img.shields.io/badge/Pytest-8.4.1-blue) – Testing framework  

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Project Structure
```
data-extraction-automation-app/
│
├── app/
│ ├── main.py 
│ ├── config.py
│ ├── generate_user_data.py
│ ├── core/
│ └──── db_connection.py
│ └──── decorators.py
│ └──── redis_client.py
│ ├── routers/
│ └──── auth.py
│ └──── data_extraction.py
│ └──── menu.py
│ └── tests/ 
│ └──── test_main.py 
├── data/
│ ├── mysql/
│ ├── redis/
├── db/
│ ├── init/
├── file_path/
├── static/
│──── images/
├── templates/
│ ├── data_extraction.html 
│ └── login.html
│ └── menu.html
```

- **app/**: Directory containing FastAPI server code  
- **app/config.py**: Centralized configuration module that loads environment variables (e.g., database credentials, Redis settings, Jira API tokens) using python-dotenv for flexible local and containerized deployment.
- **app/generate_user_data.py**: Utility script for generating synthetic user data with the Faker library and populating the MySQL database for testing and validation.
- **app/main.py**: Entry point of the FastAPI applications  
- **app/core/db_connection.py**: Provides a shared MySQL database connection object for FastAPI applications.
- **app/core/decorators.py**: Contains reusable decorators for authentication and login status checks in FastAPI.
- **app/core/redis_client.py**: Defines a shared Redis client instance used across FastAPI services.
- **app/core/template.py**: Configures and provides a Jinja2Templates instance for rendering templates in FastAPI.
- **app/routers/auth.py**: Contains route handlers for authentication, login and logout operations in the FastAPI application.
- **app/routers/data_extraction.py**: Defines endpoints and logic for data extraction workflows and requests in the FastAPI service.
- **app/routers/menu.py**: Implements the API routes for menu management and retrieval within the FastAPI application.
- **app/tests/**: Directory for test code  
- **data/mysql/**: Contains local Docker volume data for MySQL, used to persist database files during local development and testing.
- **data/redis/**: Contains local Docker volume data for Redis, used to persist cached session data during local development and testing.
- **db/init/**: Contains DDL commands that are automatically executed when the MySQL container starts, initializing the database schema and required tables for the application.
- **file_path/**: Local testing directory used to store data files attached from Jira issues, generate and save files containing sensitive (personal) data based on them, then encrypt and compress those files before reattaching them to Jira for testing purposes.
- **static/images/**: Contains static image assets (e.g., icons, logos, and UI elements) used by the FastAPI web application. These files are served directly without dynamic processing.
- **templates/**: Directory containing html files
- **templates/login.html**: User login page  
- **templates/menu.html**: Data request menu and other data-related lists(TBD)
- **templates/data_extraction.html** : Data request page

### Data Extraction Process Scenario <br />
1. Request Submission <br />
    `Requester`: Business team (e.g., Marketing, Sales, Customer Support, Management) <br />
    `Action`: Submits a formal request for data, specifying purpose, required fields, and usage. <br />
        Requested data may come in the format of files(csv/xlsx) or must be extracted using the sql. <br />
2. Initial Review <br />
    `Reviewer`: Data Analyst / Data Engineer <br />
    `Action`: Reviews whether the request is technically feasible and whether PII is involved. If requested data contains PII, then the ticket is sent to be approved by the Data Privacy Officer of Data Governance Team. <br />

3. Compliance & Privacy Approval <br />
    `Approver`: Privacy Officer  <br />
    `Action`: Verifies that the request complies with data protection regulations (GDPR, CCPA, local laws) and internal data policies. <br />

4. Data Extraction & Delivery <br />
    `Actor`: Data Analyst / Data Engineer <br />
    `Action`: Extracts the approved dataset and encyrptes the file and uploads it on Jira. <br />

### ⚙️ Automation Features
- Data team (Analyst, Engineer, Privacy Officer) / authentication and session management
- Select Jira tickets with data-request tags
- Approve PII requested data 
- Export data in files(CSV or XLSX format) or sql and uploads encrypted data on Jira
- Send notification message and password key to `requester` and `privacy officer` via slack

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- GETTING STARTED -->
## Getting Started

### Prerequisites
1. Get a free Jira API Key at [jira-api-token-url]
2. Create or Add Jira Base URL at  
3. Create or Add Slack Webhook URL at [slack-webhook-url]

### Installation
1. Git clone
2. ```docker compose up -d```
<p align="right">(<a href="#readme-top">back to top</a>)</p>

<!-- ROADMAP -->
## Roadmap
This project can be further extended to support functionalities typically found in a Customer Data Platform (CDP) or to address advanced needs of a data team, such as automated data pipelines, infrastructure management, and enhanced data governance.

<!-- CONTACT -->
## Contact
E-Mail: `chk.kim87@gmail.com` <br />
LinkedIn Profile: [linkedin-url]

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[linkedin-url]: https://linkedin.com/in/chkim87
[product-screenshot]: images/screenshot.png
[jira-api-token-url]: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/
[slack-webhook-url]: https://docs.slack.dev/messaging/sending-messages-using-incoming-webhooks/
