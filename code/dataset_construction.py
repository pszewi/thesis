# libs
import pandas as pd
import numpy as np
import recordlinkage.compare 
from bs4 import BeautifulSoup
import os

# funcs
def remove(x):
    x.remove("")
    return x   

# responsibility reports 
resp_reports_df = pd.read_csv("../data/scraping/responsibility_report_links.csv")
    
resp_reports_df["num_of_reports"] = [len(remove(eval(obs))) if '' in eval(obs) else len(eval(obs)) for obs in resp_reports_df["Download links"]]

# this is an optional dummy to look at firms that have more than 5 reports
# resp_reports_df = resp_reports_df[resp_reports_df["num_of_reports"] >=5]

# annual reports
annual_reports_df = pd.read_csv("../data/scraping/annual_report_links.csv")

# merging
merged = resp_reports_df.merge(annual_reports_df, on=["Name", "Sector", "Industry"])

# renaming, filtering, etc.
merged.rename(columns={"Company page_x":"company_page_resp", 
               "Company page_y":"company_page_ann", 
               "Download links_x":"download_links_resp",
               "Download links_y":"download_links_ann", 
               "num_of_reports":"num_of_reports_resp",
               "Name":"name", 
               "Industry":"industry", 
               "Sector":"sector"},
              inplace=True)

# making characteristic data 
merged["characteristics_dirty"] = merged["characteristics_dirty"].apply(lambda html: BeautifulSoup(html, 'html.parser'))

merged["ticker"] = merged["characteristics_dirty"].apply(lambda html: html.find("span", {"class":"ticker_name"}))
merged['ticker'] = np.where(merged["ticker"].isna(), pd.NA, merged["ticker"])
merged["ticker"] = merged["ticker"].apply(lambda html: pd.NA if type(html)==pd._libs.missing.NAType else html.text)

merged["exchange"] = merged["characteristics_dirty"].apply(lambda html: html.find("div", {"class":"right"}))
merged['exchange'] = np.where(merged["exchange"].isna(), pd.NA, merged["exchange"])
merged["exchange"] = merged["exchange"].apply(lambda html: pd.NA if type(html)==pd._libs.missing.NAType else html.text)
merged["exchange"] = merged["exchange"].str.extract(r" +(.*) ")

merged["employees"] = merged["characteristics_dirty"].apply(lambda html: html.find("li", {"class":"employees"}))
merged['employees'] = np.where(merged["employees"].isna(), pd.NA, merged["employees"])
merged["employees"] = merged["employees"].apply(lambda html: pd.NA if type(html)==pd._libs.missing.NAType else html.text)

merged["location"] = merged["characteristics_dirty"].apply(lambda html: html.find("li", {"class":"location"}))
merged['location'] = np.where(merged["location"].isna(), pd.NA, merged["location"])
merged["location"] = merged["location"].apply(lambda html: pd.NA if type(html)==pd._libs.missing.NAType else html.text)

merged["website"] = merged["characteristics_dirty"].apply(lambda html: html.find("div", {"class":"btn_visit_website"}).find("a", {"href":True}))
merged['website'] = np.where(merged["website"].isna(), pd.NA, merged["website"])
merged["website"] = merged["website"].apply(lambda html: pd.NA if type(html)==pd._libs.missing.NAType else html['href'])

merged["num_of_reports_ann"] = [len(remove(eval(obs))) if '' in eval(obs) else len(eval(obs)) for obs in merged["download_links_ann"]]
merged = merged[merged["num_of_reports_ann"] >=5]
merged["sector"] = merged["sector"].str.replace("All ", "").str.replace(" Companies", "")

# some extra descriptive columns
merged["is_lower"] = np.where(merged["num_of_reports_ann"] < merged["num_of_reports_resp"], "num_of_reports_ann", "num_of_reports_resp")

merged["is_lower"] = np.where(merged["num_of_reports_ann"] == merged["num_of_reports_resp"], "equal", merged["is_lower"])

merged["min_reports"] = np.where(merged["num_of_reports_ann"] < merged["num_of_reports_resp"], merged["num_of_reports_ann"], merged["num_of_reports_resp"])

merged = merged[['name', 'industry', 'sector', 'ticker', 'exchange', 'employees', 'location', 'website',
                 'company_page_resp', 'download_links_resp', 'num_of_reports_resp',
                 'company_page_ann', 'download_links_ann', 'num_of_reports_ann',
                 'is_lower', 'min_reports', 'year_lists']]


# checking how many firms per sector
print(merged["sector"].value_counts())
print(merged["sector"].value_counts(normalize=1))

# checking how many firms per industry (top 10 only)
print(merged["industry"].value_counts().head(10))

# making different minimum number of reports stat
print(merged["min_reports"].value_counts().head(10))

print(f"There's {sum(merged['min_reports'].value_counts().head(10)[merged['min_reports'].value_counts().head(10)<307])} companies with at least 6 reports")

print(f"There's {sum(merged['min_reports'].value_counts().head(10)[merged['min_reports'].value_counts().head(10)<181])} companies with at least 7 reports")

print(f"There's {sum(merged['min_reports'].value_counts().head(10)[merged['min_reports'].value_counts().head(10)<147])} companies with at least 8 reports")


# ////////////////////////////////////////////////
# trying to link the datasets using recordlinkage 
# ////////////////////////////////////////////////
companies_df = pd.read_excel("../data/LSEG data/test_newest.xlsx")
companies_df["ticker_test_1"] = companies_df["RIC"].str.replace(r"\..*", "", regex=True).str.replace("@", "")



# exchanges = {"London SE":"LSE", "Nasdaq":"NASDAQ", "Australian SE":"ASX", "Toronto SE":"TSX"}
companies_df["exchange"] = np.where(companies_df["BOURSE NAME"] == "London SE", "LSE", companies_df["BOURSE NAME"])
companies_df["exchange"] = np.where(companies_df["BOURSE NAME"] == "Nasdaq", "NASDAQ", companies_df["exchange"])
companies_df["exchange"] = np.where(companies_df["BOURSE NAME"] == "Australian SE", "ASX", companies_df["exchange"])
companies_df["exchange"] = np.where(companies_df["BOURSE NAME"] == "Toronto SE", "TSX", companies_df["exchange"])

# test_new

matches_easy = merged.merge(companies_df, left_on=['ticker', 'exchange'], right_on=["ticker_test_1", "exchange"])

not_matched = merged[~merged["name"].isin(matches_easy["name"])]



# -------------- matching missing values ----

companies_df["name_lower"] = companies_df["COMPANY NAME.1"].str.lower()
not_matched["name_lower"] = not_matched["name"].str.lower()

replacements = {
                "corp":"corporation",
                "inc":'incorporated',
                "ltd":"limited",
                "plc":"public limited company",
                '.':''}

for key, value in replacements.items():
    not_matched["name_lower"] = not_matched['name_lower'].str.replace(key, value)
    companies_df["name_lower"] = companies_df['name_lower'].str.replace(key, value)


test_1 = not_matched.merge(companies_df, left_on=["name_lower",'exchange'], 
                           right_on=["name_lower",'exchange'])

test_1.drop_duplicates('name', inplace=True)

matches_easy = pd.concat([matches_easy, test_1], ignore_index=True)

# update not_matched
not_matched = merged[~merged["name"].isin(matches_easy["name"])]

# trying other datasets
not_matched_comp = pd.read_excel('../data/LSEG data/not_matched.xlsx')


# ------------- matching the short name -------
not_matched['name_lower'] = not_matched['name'].str.lower()
not_matched_comp['name_lower'] = not_matched_comp["NAME"].str.lower()
not_matched_comp['ticker'] = not_matched_comp['RIC'].str.replace(r"(\..*)", '', regex=True)

test_2 = not_matched.merge(not_matched_comp, left_on='name_lower', right_on=['name_lower'])

matches_easy = pd.concat([matches_easy, test_2], ignore_index=True)
not_matched = merged[~merged["name"].isin(matches_easy["name"])]


# ------------- matching the expanded name -------
not_matched_comp["name_lower"] = not_matched_comp["COMPANY NAME.1"].str.lower()
not_matched["name_lower"] = not_matched["name"].str.lower()

replacements = {
                "corp":"corporation",
                "inc":'incorporated',
                "ltd":"limited",
                "plc":"public limited company",
                '.':''}

for key, value in replacements.items():
    not_matched["name_lower"] = not_matched['name_lower'].str.replace(key, value)
    not_matched_comp["name_lower"] = not_matched_comp['name_lower'].str.replace(key, value)


test_3 = not_matched.merge(not_matched_comp, left_on=["name_lower"], 
                           right_on=["name_lower"])


matches_easy = pd.concat([matches_easy, test_3], ignore_index=True)
not_matched = merged[~merged["name"].isin(matches_easy["name"])]

# ------------- making a shortened name var -------
not_matched_comp["name_short"] = not_matched_comp["COMPANY NAME.1"].str.lower()
not_matched["name_short"] = not_matched["name"].str.lower()
replacements = {
                'limited':'',
                'incorporated':'',
                "company":"",
                "industries":"",
                'group':'',
                'groep':'',
                "corporation":"",
                "corp":"",
                "inc":'',
                "ltd":"",
                "plc":"", 
                'nv':'', 
                'ag':'',
                'co':'',
                's.p.a':'',
                's.p':'',
                '.':'',
                ',':''
}

for key, value in replacements.items():
    not_matched["name_short"] = not_matched['name_short'].str.replace(key, value)
    not_matched_comp["name_short"] = not_matched_comp['name_short'].str.replace(key, value)

not_matched["name_short"] = not_matched['name_short'].str.strip()
not_matched_comp["name_short"] = not_matched_comp['name_short'].str.strip()

test_4 = not_matched.merge(not_matched_comp, on='name_short')
test_4.drop_duplicates('name', inplace=True)


matches_easy = pd.concat([matches_easy, test_4], ignore_index=True)
not_matched = not_matched[~not_matched["name"].isin(test_4["name"])]


# ------------- making a shortened name var with the other dataset -------
companies_df["name_short"] = companies_df["COMPANY NAME.1"].str.lower()
not_matched["name_short"] = not_matched["name"].str.lower()

replacements = {
                'limited':'',
                'incorporated':'',
                "company":"",
                "industries":"",
                'group':'',
                'groep':'',
                "corporation":"",
                "corp":"",
                "inc":'',
                "ltd":"",
                "plc":"", 
                'nv':'', 
                'ag':'',
                'co':'',
                's.p.a':'',
                's.p.':'',
                '.':'',
                ',':''
}

for key, value in replacements.items():
    not_matched["name_short"] = not_matched['name_short'].str.replace(key, value)
    companies_df["name_short"] = companies_df['name_short'].str.replace(key, value)

not_matched["name_short"] = not_matched['name_short'].str.strip()
companies_df["name_short"] = companies_df['name_short'].str.strip()

test_5 = not_matched.merge(companies_df, on='name_short')
test_5.drop_duplicates('name', inplace=True)


matches_easy = pd.concat([matches_easy, test_5], ignore_index=True)
not_matched = not_matched[~not_matched["name"].isin(test_5["name"])]

matched_final = matches_easy[['Type', 'NAME', 'RIC','MNEMONIC', 'name',
                              'BOURSE NAME', 'ICB INDUSTRY MNEM',
                              'ICB SECTOR MNEM', 'ICB INDUSTRY NAME', 'ICB SECTOR NAME',
                              'CTRY OF DOM -NAME', 'CTRY OF INC -NAME', 'employees', 'website',
                              'year_lists'
                              ]]

matched_final.rename(columns={'Type':'TYPE',
                              'name':'NAME_SCRAPED',
                              'BOURSE NAME':'BOURSE_NAME',
                              'ICB INDUSTRY MNEM':'ICB_INDUSTRY_MNEM',
                              'ICB SECTOR MNEM':'ICB_SECTOR_MNEM',
                              'ICB INDUSTRY NAME':'ICB_INDUSTRY_NAME',
                              'ICB SECTOR NAME':'ICB_SECTOR_NAME',
                              'CTRY OF DOM -NAME':'CTRY_OF_DOM_NAME',
                              'CTRY OF INC -NAME':'CTRY_OF_INC_NAME',
                              'employees':'EMPLOYEES',
                              'website':'WEBSITE',
                              'year_lists':'REPORT_LISTS'}, inplace=True)



matched_final.to_excel('../data/LSEG data/matched_final.xlsx')

# ------------------------------------------------
# ----------------- retired code -----------------
# ------------------------------------------------

# ----------------- record linkage -----------
# import recordlinkage

# indexer = recordlinkage.Index()

# indexer.full()

# pairs = indexer.index(not_matched, not_matched_comp)

# comp = recordlinkage.Compare()

# comp.string("name_short", "name_short", threshold=0.9)

# potential_matches = comp.compute(pairs, not_matched, not_matched_comp)
# matches = potential_matches[potential_matches.sum(axis=1)>0]


# matches_index_left = matches.index.get_level_values(0)
# matches_index_right = matches.index.get_level_values(1)

# test_left = merged.reindex(matches_index_left).reset_index()

# test_right = companies_df.reindex(matches_index_right).reset_index()

# test_6 = pd.concat([test_left, test_right], axis=1, ignore_index=True)


