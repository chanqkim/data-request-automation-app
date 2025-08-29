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
│ ├── core/
│ └──── templates.py
│ └── tests/ 
│ └──── test_main.py 
└── templates/ 
├──── login.html 
├──── menu.html 
```

- **app/**: Directory containing FastAPI server code  
- **app/main.py**: Entry point of the FastAPI applications  
- **app/core/template.py**: Common Jinja2Templates object for FastAPI applications  
- **app/tests/**: Directory for test code  
- **templates/**: Stores HTML template files  
- **login.html**: User login page  
- **menu.html**: Data request other data-related lists

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


### Installation
1. Git clone
2. ```uvicorn app.main:app --reload```
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