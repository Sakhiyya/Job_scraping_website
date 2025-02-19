import requests
from bs4 import BeautifulSoup 
import pandas as pd 
import matplotlib.pyplot as plt 
from statsmodels.tsa.arima.model import ARIMA 
import numpy as np 
import time 
import schedule  
from tkinter import messagebox
import tkinter as tk
import threading  
import os 
from PIL import Image, ImageTk 


scheduler_thread = None 


def ensure_plots_directory():
    if not os.path.exists('plots'): 
        os.makedirs('plots') 


def extract_job_data(url):
    print(f"Extracting job data from {url}...")
    try:
        response = requests.get(url) # sends a GET request to the URL
        response.raise_for_status() # raise an error if the request was not successful
    except requests.RequestException as e:
        print(f"Failed to retrieve data from {url}. Error: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser') 
    job_elements = soup.find_all('div', class_='module job-result') 

    jobs = [] 
    for job_element in job_elements:
        try:
            # extract job details
            title = job_element.find('h2', itemprop='title').text.strip()
            company = job_element.find('h3', itemprop='name').text.strip()
            location = job_element.find('li', class_='location').text.strip()
            salary = job_element.find('li', class_='salary').text.strip()
            date_posted = job_element.find('li', class_='updated-time').text.strip()
            closing_date = job_element.find('li', class_='closed-time').text.strip()
            
            jobs.append({
                'Job_Title': title,
                'Company': company,
                'Job_Location': location,
                'Job_Salary': salary,
                'Date Posted': date_posted,
                'Closing Date': closing_date
            })
        except AttributeError as e:
            print(f"Error parsing job element: {e}")

    print(f"Extracted {len(jobs)} job postings from {url}.")
    return jobs


def collect_and_save_jobs():
    """Collect job data from multiple URLs, save to CSV, and generate charts."""
    print("Starting collect_and_save_jobs function...")
    urls = [
        'https://www.myjob.mu/Jobs/Banking/',
        'https://www.myjob.mu/Jobs/Agriculture-Fishing/',
        'https://www.myjob.mu/Jobs/Insurance/'
    ]

    job_data = [] 
    for url in urls:
        job_data.extend(extract_job_data(url)) 

    # converting the job data list to a panda dataframe
    # then saving the dataframe to a CSV file.
    if job_data:
        df = pd.DataFrame(job_data)
        df.to_csv('job_info.csv', index=False)
        print("Job data saved to 'job_info.csv'")
        create_charts(df) # the data frame is passed to the create_charts function.
    else:
        print("No job data to save or plot.")


def create_charts(df):
    ensure_plots_directory() # this function is called to make sure that the plots directory exists.
    print("Creating charts...")

    try:
        # Bar Chart
        company_counts = df['Company'].value_counts()
        colors = plt.cm.viridis(np.linspace(0, 1, len(company_counts))) 
        plt.figure(figsize=(12, 7)) 
        company_counts.plot(kind='bar', color=colors, edgecolor='purple') # plot the chart
        plt.title('Number of Jobs per Company', fontsize=16, fontweight='bold')
        plt.xlabel('Company', fontsize=14)
        plt.ylabel('Number of Jobs', fontsize=14)
        plt.xticks(rotation=45, ha='right', fontsize=12)
        plt.yticks(fontsize=12)
        plt.grid(axis='y', linestyle='dashdot', alpha=0.7)
        for i, count in enumerate(company_counts):
            plt.text(i, count + 0.5, str(count), ha='center', va='bottom', fontsize=11, fontweight='bold') # add count to each bar that display the number of job posting for each company
        plt.tight_layout()
        plt.savefig('plots/jobs_per_company_bar_chart.png')
        plt.close()
        print("Bar chart saved successfully.")

        # Pie Chart
        location_counts = df['Job_Location'].value_counts()
        colors = plt.cm.Set3(np.linspace(0, 1, len(location_counts)))
        explode = [0.1] + [0] * (len(location_counts) - 1) 
        plt.figure(figsize=(6, 6)) 
        plt.pie(location_counts, labels=location_counts.index, autopct='%1.1f%%', startangle=140,
                colors=colors, explode=explode, shadow=True, wedgeprops={'edgecolor': 'pink'}) 
        centre_circle = plt.Circle((0, 0), 0.70, fc='white')
        plt.gca().add_artist(centre_circle) # add the centre circle to the chart
        plt.title('Job Location Distribution', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig('plots/job_location_pie_chart.png')
        plt.close()
        print("Pie chart saved successfully.")

        # Line Chart
        df['Date Posted'] = df['Date Posted'].str.replace('Added ', '')
        df['Date Posted'] = pd.to_datetime(df['Date Posted'], format='%d/%m/%Y', errors='coerce') 
        df = df.dropna(subset=['Date Posted']) 

        posted_trend = df['Date Posted'].value_counts().sort_index() # count the number of jobs posted on each date 
        posted_trend = posted_trend.asfreq('D').fillna(0)
        posted_trend_smoothed = posted_trend.rolling(window=7).mean() # smooth the trend using a 7-day moving average

        model = ARIMA(posted_trend, order=(5, 1, 0))
        model_fit = model.fit()

        forecast_steps = 30  # The forecast will extend 30 days into the future
        forecast = model_fit.forecast(steps=forecast_steps) # generate the forecast
        future_dates = pd.date_range(start=posted_trend.index[-1] + pd.Timedelta(days=1), periods=forecast_steps) # creates a list of future dates corresponding to the forecast period.
        forecast_series = pd.Series(forecast, index=future_dates)

        plt.figure(figsize=(10, 6))
        plt.plot(posted_trend.index, posted_trend, label='Actual Job Postings')
        plt.plot(posted_trend_smoothed.index, posted_trend_smoothed, label='Smoothed Job Postings (7-day MA)', color='pink')
        plt.plot(forecast_series.index, forecast_series, label='Predicted Job Postings', color='purple', linestyle='--')
        plt.title('Trend and Forecast of Job Postings', fontsize=16, fontweight='bold')
        plt.xlabel('Date', fontsize=14)
        plt.ylabel('Number of Job Postings', fontsize=14)
        plt.legend()
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig('plots/job_posting_trend_line_chart.png')
        plt.close()
        print("Line chart saved successfully.")

        # Histogram
        plot_histogram(df, 'Job_Salary', 'job_salary_histogram.png')
        print("Histogram saved successfully.")

        # Area Graph
        plot_area_graph(df, 'Job_Salary', 'job_salary_area_graph.png')
        print("Area graph saved successfully.")

    except Exception as e:
        print(f"Failed to create charts: {e}")


def plot_histogram(df, column_name, output_filename):
    plt.figure(figsize=(10, 6))
    plt.hist(df[column_name].dropna(), bins=11, color='lightpink', edgecolor='pink', alpha=0.7, rwidth= 0.95)
    plt.title(f'Frequency of job salaries', fontsize=16, fontweight='bold')
    plt.xlabel('job salary', fontsize=14, fontweight='bold')
    plt.ylabel('Frequency', fontsize=14, fontweight='bold')
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(f'plots/{output_filename}')
    plt.close()


def plot_area_graph(df, column_name, output_filename):
    counts = df[column_name].value_counts()
    plt.figure(figsize=(10, 6))
    plt.fill_between(counts.index, counts.values, color='lightpink', alpha=0.4)
    plt.plot(counts.index, counts.values, color='pink', alpha=0.6, linewidth=2)
    plt.title(f'Trend in Job salary distribution', fontsize=16, fontweight='bold')
    plt.xlabel('job salary', fontsize=14, fontweight='bold')
    plt.ylabel('Number of Job Postings', fontsize=14, fontweight='bold')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(f'plots/{output_filename}')
    plt.close()


def job():
    print("Running scheduled job...")
    collect_and_save_jobs() # call the function to collect and save job data.


def run_script(): # run the script manually
    try:
        print("Manually running job...")
        collect_and_save_jobs() # call the function to collect and save job data when run manually
        messagebox.showinfo("Success", "Script executed successfully!")
    except Exception as e:
        print(f"Error: {e}")
        messagebox.showerror("Error", f"Failed to execute script: {e}")


def start_scheduler(schedule_time): 
    global scheduler_thread
    if scheduler_thread is not None and scheduler_thread.is_alive(): # checks if the schedule is already running.
        print("Scheduler is already running.")
        return

    schedule.clear() 
    schedule.every().day.at(schedule_time).do(job) # Schedule the job to run daily at the specified time
    print(f"Scheduler set to run at {schedule_time} daily.")

    scheduler_thread = threading.Thread(target=_run_scheduler) # create a new thread to run the scheduler in the background 
    scheduler_thread.daemon = True # it exits when the main program exits
    scheduler_thread.start() 

def _run_scheduler(): # run the schedular in a loop
    while True:
        schedule.run_pending() # Run any pending scheduled jobs
        time.sleep(1) # wait for 1 sec before checking again


def stop_scheduler():
    schedule.clear()
    print("Scheduler stopped.")
    messagebox.showinfo("Scheduler Stopped", "The scheduler has been stopped.")


def view_plots():
    files = [
        'plots/jobs_per_company_bar_chart.png',
        'plots/job_location_pie_chart.png',
        'plots/job_posting_trend_line_chart.png',
        'plots/job_salary_histogram.png',
        'plots/job_salary_area_graph.png'
    ]

    def show_image(file_path): # show images of the plots
        img = Image.open(file_path) # open image file
        img = ImageTk.PhotoImage(img) # convert image to photoimage for Tkinter

        top = tk.Toplevel()
        top.title(file_path)
        tk.Label(top, image=img).pack()
        top.img = img

    root = tk.Toplevel()  # Create a new top-level window for viewing plots
    root.title("View Plots")

    for file in files: # Create a button for each plot file
        button = tk.Button(root, text=f"View {os.path.basename(file)}", command=lambda f=file: show_image(f))
        button.pack(pady=5)


def create_gui():
    root = tk.Tk() # create the main Tkinter window
    root.title("Job Data Collector")

    tk.Label(root, text="Enter Time for Scheduling (HH:MM):", font=('Comic sans MS', 12)).pack(pady=5)
    time_entry = tk.Entry(root, font=('Comic sans MS', 12))
    time_entry.pack(pady=5)

    def on_start_scheduler(): #  function that start the schedular
        time = time_entry.get() # take the user inputted time value and assign it to time
        if not time:
            messagebox.showwarning("Input Error", "Please enter a time in HH:MM format.")
            return
        start_scheduler(time)

    run_button = tk.Button(root, text="Run Job Now", command=run_script, padx=10, pady=5,
    font=('Comic sans MS', 14, 'bold'), bg='#FFB6C1', fg='white', relief='raised', borderwidth=2)
    run_button.pack(pady=10)

    start_scheduler_button = tk.Button(root, text="Start Scheduler", command=on_start_scheduler, padx=10, pady=5,
    font=('Comic sans MS', 14, 'bold'), bg='#ADD8E6', fg='white', relief='raised', borderwidth=2)
    start_scheduler_button.pack(pady=10)

    stop_scheduler_button = tk.Button(root, text="Stop Scheduler", command=stop_scheduler, padx=10, pady=5,
    font=('Comic sans MS', 14, 'bold'), bg='#90EE90', fg='white', relief='raised', borderwidth=2)
    stop_scheduler_button.pack(pady=10)

    view_plots_button = tk.Button(root, text="View Plots", command=view_plots, padx=10, pady=5,
    font=('Comic sans MS', 14, 'bold'), bg='#FDFD96', fg='white', relief='raised', borderwidth=2)
    view_plots_button.pack(pady=10)

    quit_button = tk.Button(root, text="Exit", command=root.quit, padx=10, pady=5,
    font=('Comic sans MS', 14, 'bold'), bg='#D8BFD8', fg='white', relief='raised', borderwidth=2)
    quit_button.pack(pady=10)

    root.mainloop() 


if __name__ == "__main__":
    create_gui()
