import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

def extract_job_data(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    job_elements = soup.find_all('div', class_='module job-result')

    jobs = []
    for job in job_elements:
        try:
            title = job.find('h2', itemprop='title').text.strip()
            company = job.find('h3', itemprop='name').text.strip()
            location = job.find('li', class_='location').text.strip()
            salary = job.find('li', class_='salary').text.strip()
            posted = job.find('li', class_='updated-time').text.strip()
            closing = job.find('li', class_='closed-time').text.strip()

            jobs.append({
                'Job_Title': title,
                'Company': company,
                'Job_Location': location,
                'Job_Salary': salary,
                'Date Posted': posted,
                'Closing Date': closing
            })
        except AttributeError:
            continue

    return jobs

def collect_and_save_jobs():
    urls = [
        'https://www.myjob.mu/Jobs/Banking/',
        'https://www.myjob.mu/Jobs/Agriculture-Fishing/',
        'https://www.myjob.mu/Jobs/Insurance/'
    ]

    all_jobs = []
    for url in urls:
        all_jobs.extend(extract_job_data(url))

    if all_jobs:
        df = pd.DataFrame(all_jobs)
        df.to_csv('job_info.csv', index=False)
        print("✅ Job data updated.")
    else:
        print("❗No job data found.")
