# ////////////////////////////////////////////////
#                  LIBS
# ////////////////////////////////////////////////

import pandas as pd
import requests
from bs4 import BeautifulSoup, SoupStrainer
from fake_useragent import UserAgent
import os
from concurrent.futures import ThreadPoolExecutor 
from itertools import repeat
import traceback

# ////////////////////////////////////////////////
#                       FUNCS
# ////////////////////////////////////////////////




def pdf_download(link, directory):
    ua = UserAgent()
    hdr = {"User-Agent":ua.random}
    
    filename = link.split('/')[-1]
    if not filename.endswith(".pdf"):
        filename = filename + ".pdf"
    
    try:
        req = requests.get(link, headers=hdr).content
        with open(directory + "/" + filename, mode="wb") as file:
            file.write(req)
    except:
        traceback.print_exc(file=None)
        print(f"Where the error ocurred:{directory}")
        with open("exceptions.log", "a") as logfile:
            traceback.print_exc(file=logfile)
            print(f"Where the error ocurred:{directory}")
   
    
def scraping_loop(df, dir, scrape_column):
    # starting the loop for scraping
    for index, row in df.iterrows():


        # making a directory for each company 
        folder_dir = dir
        company_folder_dir = row["name"].lower().replace(" ", "_")
        
        if any(i in company_folder_dir for i in ("?", "|")):
            company_folder_dir = company_folder_dir.replace("?", "")
            company_folder_dir = company_folder_dir.replace("|", "")
        
        total_dir = folder_dir + company_folder_dir
        if os.path.exists(total_dir):
            continue
        
        else:    
            if not os.path.exists(total_dir):
                os.makedirs(total_dir)

            # if "" on the list, drop it 
            download_links = eval(row[scrape_column]) 
            if "" in download_links:
                download_links.remove("")
                
            # download files using multithreading
            with ThreadPoolExecutor() as executor:
                executor.map(pdf_download, download_links, repeat(total_dir))

def get_index(main_link, sector_dirs, df):
    # there's 9 pages of index so that's why the loop goes from 1 to 9
    for i in range(1,10):
        # getting the source page
        print(i)
        
        source = requests.get(main_link+sector_dirs+f"{i}", headers=fake_headers)
        print(source.status_code)
        strainer = SoupStrainer("section", {"class":"category_section"})

        content = BeautifulSoup(source.content, "html.parser", parse_only=strainer)

        sector_data = content.find("h1")
        industry_data = content.find_all("span", attrs={"class":"industryName"})
        company_link_tags = content.find_all("span", attrs={"class":"companyName"})


        company_names = []
        company_links = []
        company_industry = []
        for link_num in range(0, len(company_link_tags)):
            company_names.append(company_link_tags[link_num].contents[0].get_text())
            company_industry.append(industry_data[link_num].get_text()) 
            company_links.append(company_link_tags[link_num].contents[0].get("href"))
            
            
            
        temp_df =  pd.DataFrame({
            "name":company_names, 
            "industry":company_industry, 
            "sector": [sector_data.get_text()]*len(company_names),
            "company page": [main_link + company_link for company_link in company_links]
        })
        
        df = pd.concat([df, temp_df], axis=0, ignore_index=True)
    return df

def get_download_links(df, main_link, company_link_col, output_col):
    for company in range(0, len(df)):

        try:
            company_page = requests.get(df.iloc[company, company_link_col], headers=fake_headers).content
            
            # most recent article
            recent_soup = BeautifulSoup(company_page, "html.parser", parse_only=SoupStrainer("div", {"class":"most_recent_content_block"}))

            recent_tags = recent_soup.find_all("a", attrs={"class":"btn_form_10k"})
            if recent_tags:
                recent_link = main_link + recent_tags[0].get("href")
            else:
                recent_link = ""
                
            # archived articles
            archived_soup = BeautifulSoup(company_page, "html.parser", parse_only=SoupStrainer("div", {"class":"archived_report_content_block"}))
            
            archived_tags = archived_soup.find_all("span", attrs={"class":"btn_archived view_annual_report"})

            archived_links = []
            for report in archived_tags:
                temp = report.find("a").get("href")
                archived_links.append(temp)
                
            links_list = [recent_link] + [link if link.startswith("https://") else main_link + link for link in archived_links ]
            df.iat[company, output_col] = links_list
        except Exception as e:
            print(company, e)
    
    return df

def get_company_charachteristics(df, main_link, company_link_col, output_col_unstructured, output_col_years):
    for company in range(0, len(df)):
        try:
            company_page = requests.get(df.iloc[company, company_link_col], headers=fake_headers).content 
            # company data
            data_soup = BeautifulSoup(company_page, "html.parser", parse_only=SoupStrainer("div", {"class":"left_section"}))
            
            df.iat[company, output_col_unstructured] = data_soup
            
            most_recent_year_name = BeautifulSoup(company_page, "html.parser", parse_only=SoupStrainer("div", {"class":"most_recent_content_block"})).find("span", {"class":"bold_txt"}).text
            
            archived_year_names = BeautifulSoup(company_page, "html.parser", parse_only=SoupStrainer("div", {"class":"archived_report_content_block"})).find_all("span", {"class":"heading"})
            year_names = [year.text for year in archived_year_names]
            
            df.iat[company, output_col_years] = [most_recent_year_name] + year_names
            

        
        except Exception as e:
            print(company, e)
    
    return df


# ////////////////////////////////////////////////
#                  FIRST WEBSITE
# ////////////////////////////////////////////////

# initial website
main_link = "https://www.responsibilityreports.com"

# link with sectors to collect
sector_dirs = "/Companies?sect="

# fake user agent
ua = UserAgent()
fake_headers = {"User-Agent":ua.random}


# making an empty df before getting the index 
resp_reports_df = pd.DataFrame({
    "name":[],
    "industry":[],
    "sector":[],
    "company page":[]
    })


resp_reports_df = get_index(main_link, sector_dirs, resp_reports_df)
        
            
# making an empty column for the download links
resp_reports_df["download links"] = pd.NA


# getting the download links
resp_reports_df = get_download_links(resp_reports_df, main_link, 3, 4)


resp_reports_df["characteristics_dirty"] = pd.NA
resp_reports_df["year_lists"] = pd.NA
# getting the comp charachteristics
resp_reports_df = get_company_charachteristics(resp_reports_df, main_link, 3, 5, 6)


# writing to csv
# resp_reports_df.to_csv("data/scraping/responsibility_report_links.csv", index=False)


# re-loading it here so I wouldn't have to repeat the process everytime
# resp_reports_df_data = pd.read_csv("data/scraping/responsibility_report_links.csv")

# scraping
scraping_loop(resp_reports_df, "data/scraping/resp_reports/", "download links")
    
# quick helper function for returning the list after removing the whitespace
def remove(x):
    x.remove("")
    return x   
    
resp_reports_df["num_of_reports"] = [len(remove(eval(obs))) if '' in eval(obs) else len(eval(obs)) for obs in resp_reports_df["download links"]]

# NOTE
# about 1400 companies with at least 5 reports, 1000 with at least 6.
# probably should start taking from 5>= and then subset the scraping for these to see whether I can get a large enough of a dataset from that 
# later figure it out from there with the ESG measures and such 




# //////////////////////////////////////////////////////////////////////////////////////////////////
#                                          SECOND WEBSITE
# //////////////////////////////////////////////////////////////////////////////////////////////////

# initial website
main_link = "https://www.annualreports.com/"

# link with sectors to collect
sector_dirs = "/Companies?sect="

# fake user agent
ua = UserAgent()
fake_headers = {"User-Agent":ua.random}


# get link to each company page 
annual_reports_df = pd.DataFrame({
    "name":[],
    "industry":[],
    "sector":[],
    "company page":[]
    })

annual_reports_df = get_index(main_link, sector_dirs, annual_reports_df)
        
            
# making an empty column for the download links
annual_reports_df["download links"] = pd.NA


# getting the download links
annual_reports_df = get_download_links(annual_reports_df, main_link, 3, 4)


# writing to csv
# annual_reports_df.to_csv("data/scraping/annual_report_links.csv", index=False)


# re-loading it here so I wouldn't have to repeat the process everytime
# annual_reports_df = pd.read_csv("../data/scraping/annual_report_links.csv")

# NOTE I merged the dfs to see what firms will have >=5 both sustainability and annual reports (deemed as minimum sufficient data)
# NOTE Then I use it to be able to download less of the data (because there's a lot of waste otherwise)
resp_reports_df = resp_reports_df[resp_reports_df["num_of_reports"] >=5]

merged = resp_reports_df.merge(annual_reports_df, on=["name", "sector", "industry"])

merged.rename(columns={"company page_x":"company_page_resp", 
               "company page_y":"company_page_ann", 
               "download links_x":"download_links_resp",
               "download links_y":"download_links_ann", 
               "num_of_reports":"num_of_reports_resp",},
              inplace=True)


merged["num_of_reports_ann"] = [len(remove(eval(obs))) if '' in eval(obs) else len(eval(obs)) for obs in merged["download_links_ann"]]

merged = merged[merged["num_of_reports_ann"] >=5]



# actual scraping
# call the function
scraping_loop(merged, "data/scraping/annual_reports/", "download_links_ann")