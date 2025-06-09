# file with user-defined functions
import pandas as pd
import pymupdf
import numpy as np
from os import listdir, makedirs
from os.path import exists
from re import search, findall
from traceback import print_exc
from json import dump, load
from datasets import Dataset
from transformers.pipelines.pt_utils import KeyDataset
from datasets import Dataset
import statsmodels.api as sm
from itertools import product
from datetime import datetime

def ExtractNameYear(series_names, input_dir, nlp_model, year_str):
    '''Extracts the first page of each document and checks the year of release.'''
    
    filename_year_dict = {}
    for row in series_names:
        company_name = row.lower().replace(" ", "_")
        
        if any(i in company_name for i in ("?", "|")):
            company_name = company_name.replace("?", "")
            company_name = company_name.replace("|", "")
        
        company_dir = input_dir + "/" + company_name      
        
        list_of_paths = [company_dir + f"/{file}" for file in listdir(company_dir)]
        
        
        for file in list_of_paths:    
            try:
                with pymupdf.open(file) as doc:
                    pages = doc[0].get_text()
                    
                    doc = nlp_model(pages)
                    sentences = list(doc.sents)
                    num = [m.group() for sent in sentences if (m := search(r"\d+", sent.text))] 
                    
                    
                    if year_str in num:
                        filename = search(r"(.*)\/(.*)", file)[2]
                        filename_year_dict[company_name] = (filename, file)
                    else:
                        continue
                    
            except Exception as e:
                with open("_exceptions.log", "a") as logfile:
                    print_exc(file=logfile)
                    logfile.write(rf"The company that the error occured on:{company_name}\n")
                    logfile.write(f"The file that the error occured on:{file}")
        
    return filename_year_dict    



def ExtractFileName(series_names, input_dir, year_str):
    '''Extracts the name of each document (from filename) and checks the year of release.'''
    
    filename_year_dict = {}
    for row in series_names:
        company_name = row.lower().replace(" ", "_")
        
        if any(i in company_name for i in ("?", "|")):
            company_name = company_name.replace("?", "")
            company_name = company_name.replace("|", "")
        
        company_dir = input_dir + "/" + company_name      
        
        
        for file in listdir(company_dir):    
            try:
                file_year = findall(r"_\d+|\d+", file)
                year = "_" + year_str
                
                if year in file_year:
                    path = company_dir + f"/{file}"
                    filename_year_dict[company_name] = (file, path)
                else:
                    continue
                
                
            except Exception as e:
                with open("_exceptions_filename.log", "a") as logfile:
                    print_exc(file=logfile)
                    logfile.write(rf"The company that the error occured on:{company_name}\n")
                    logfile.write(f"The file that the error occured on:{file}")
        
    return filename_year_dict    


def ExtractAllText(filename_dict, year_str, output_path):
    
    if not exists(output_path + "/" + year_str):
        makedirs(output_path + "/" + year_str)
    
    
    
    for key in filename_dict.keys():
        
        if exists(output_path + "/" + year_str + "/" + key + ".json"):
            continue
    
        try:
            with pymupdf.open(filename_dict[key][1]) as doc:
                blocks = [page.get_text('blocks') for page in doc]
                sents = []
                
                for page in blocks:
                    for par in page:
                        par_list = par[4].split(" ")
                        if (len(par_list) >= 20) and (par[4].count("\n")>=3) and ('.' in par[4]) and ((sum(ch.isalpha() for ch in par[4]) / max(len(par[4]), 1)) >= 0.7):
                            sents.append(par[4]) 
            
            with open(output_path + "/" + year_str + "/" + key + ".json", "w") as file:
                dump(sents, file)
                    
        except Exception as e:
            with open(output_path + "/" + year_str + "/" + "_exceptions_all_text.log", "a") as logfile:
                logfile.write(rf"The company that the error occured on:{key}\n")
                print_exc(file=logfile)
   
def Classify(sentences, pipe):
    classifiers = []
    scores = []
    
    dataset = Dataset.from_pandas(pd.DataFrame({"sentences":sentences}))
    
    for out in pipe(KeyDataset(dataset, 'sentences'), padding=True, truncation=True):
        classifiers.append(out["label"])
        scores.append(out["score"])
        
    df = pd.DataFrame({'texts':sentences,
                     'classifier':classifiers, 
                     "score":scores})
    
    return df
        

def ComputeGreenInd(series_name, input_dir, pipe_class, pipe_spec): 
    
    clim_related_nums = []
    non_spec_nums = []
    green_inds = []
    for row in series_name:
        try:
            company_name = row.lower().replace(" ", "_")
            
            if any(i in company_name for i in ("?", "|")):
                company_name = company_name.replace("?", "")
                company_name = company_name.replace("|", "")
            
            company_dir = input_dir + "/" + company_name + '.json'
            
            with open(company_dir, 'r') as file:
                txt_list = load(file)
            
            class_df = Classify(txt_list, pipe_class)
            
            class_df = class_df.loc[class_df["classifier"]=="yes"]
            
            spec_df = Classify(class_df["texts"].to_list(), pipe_spec)
            
            non_spec_df = spec_df.loc[spec_df["classifier"]=="non"]
            
            num_clim_related = len(class_df)
            num_non_spec = len(non_spec_df)
            green_ind = (num_non_spec+1)/(num_clim_related+1) 
            
            clim_related_nums.append(num_clim_related)  
            non_spec_nums.append(num_non_spec)
            green_inds.append(green_ind)

        except Exception as e:
            clim_related_nums.append(pd.NA)  
            non_spec_nums.append(pd.NA)
            green_inds.append(pd.NA)
            with open(f"{input_dir}/_exceptions_green_ind.log", "a") as logfile:
                logfile.write(rf"The company that the error occured on:{row}\n")
                print_exc(file=logfile)
                
        
    df = pd.DataFrame({"NAME":series_name, 
                    'CLIMATE_REL':clim_related_nums, 
                    "NON_SPEC":non_spec_nums,
                    "GREEN_IND":green_inds
                    })
        
            
    return df


def TransformReturns(df, df_characteristic, old=False):
    if old==True:
        df = df[(df['Retrieving...'].str.contains("PRICE INDEX")) | (df['Retrieving...'].str.contains("TOT RETURN IND"))]
        df.loc[:,"NAME"] = df.loc[:,"Retrieving..."].str.removesuffix(' - PRICE INDEX').str.removesuffix(" - TOT RETURN IND")
        df.loc[:, "VARIABLE"] = np.where(df.loc[:,"Retrieving..."].str.contains(" - PRICE INDEX"), 'PRICE INDEX', pd.NA)
        df.loc[:, "VARIABLE"] = np.where(df.loc[:,"Retrieving..."].str.contains(" - TOT RETURN IND"), 'TOT RETURN IND', df.loc[:, "VARIABLE"])


        df.drop(["Retrieving..."], axis=1, inplace=True)
        df = pd.melt(df, id_vars=['NAME', "VARIABLE"]).pivot_table(index=['NAME', 'variable'], columns='VARIABLE', values='value').reset_index().rename(columns={'variable':'DATE'})
        df = df.merge(df_characteristic[['NAME', 'CTRY_OF_DOM_NAME', 'BOURSE_NAME']], how="left", on="NAME")

        df["DATE"] = df["DATE"].dt.date
    
    else:   
        df = df[df['Name'].str.contains("PRICE INDEX")]
        df.loc[:,"NAME"] = df.loc[:,"Name"].str.removesuffix(' - PRICE INDEX')
        df.loc[:, "VARIABLE"] = np.where(df.loc[:,"Name"].str.contains(" - PRICE INDEX"), 'PRICE INDEX', pd.NA)


        df.drop(["Name", 'CURRENCY'], axis=1, inplace=True)
        df = pd.melt(df, id_vars=['NAME', "VARIABLE"]).pivot_table(index=['NAME', 'variable'], columns='VARIABLE', values='value').reset_index().rename(columns={'variable':'DATE'})
        df = df.merge(df_characteristic[['NAME', 'CTRY_OF_DOM_NAME', 'BOURSE_NAME']], how="left", on="NAME")

        df["DATE"] = df["DATE"].dt.date

    return df    

def TransformIndices(df, weekly=False):
    if weekly==True:
        pass
        df.loc[:,"NAME"] = df.loc[:,"Name"].str.removesuffix(' - PRICE INDEX')
        df.loc[:, "VARIABLE"] = np.where(df.loc[:,"Name"].str.contains(" - PRICE INDEX"), 'PRICE INDEX', pd.NA)
        df.drop(columns=['Name','CURRENCY', 'MSEFLA$', 'NA'], inplace=True)

        df = pd.melt(df, id_vars=['NAME', "VARIABLE"]).pivot_table(index=['NAME', 'variable'], columns='VARIABLE', values='value').reset_index().rename(columns={'variable':'DATE'})

        df["DATE"] = df["DATE"].dt.date

    else:
        df.loc[:,"NAME"] = df.loc[:,"Name"].str.removesuffix(' - PRICE INDEX')
        df.loc[:, "VARIABLE"] = np.where(df.loc[:,"Name"].str.contains(" - PRICE INDEX"), 'PRICE INDEX', pd.NA)
        df.drop(columns=['Name', 'CURRENCY'], inplace=True)

        df = pd.melt(df, id_vars=['NAME', "VARIABLE"]).pivot_table(index=['NAME', 'variable'], columns='VARIABLE', values='value').reset_index().rename(columns={'variable':'DATE'})

        df["DATE"] = df["DATE"].dt.date



    return df

        
def MakeReturnsInd(df_ind):
    # creating monthly returns for indices
    df_ind['INDEX_PCT_RETURN'] = df_ind.groupby(by='NAME')['PRICE INDEX'].apply(pd.Series.pct_change).reset_index()['PRICE INDEX']
    df_ind["LOG_IND"] = np.log(1+df_ind["PRICE INDEX"].astype(float))
    df_ind['INDEX_LOG_RETURN'] = df_ind.groupby(by='NAME')['LOG_IND'].apply(pd.Series.diff).reset_index()['LOG_IND']
    df_ind = df_ind[['NAME', 'DATE','INDEX_PCT_RETURN', 'INDEX_LOG_RETURN']]
    
    return df_ind

def MakeReturns(df):
    # creating percentage returns for equities
    df['STOCK_PCT_RETURN'] = df.groupby(by='NAME')['PRICE INDEX'].apply(pd.Series.pct_change).reset_index()['PRICE INDEX']
    df["LOG_IND"] = np.log(1+df["PRICE INDEX"].astype(float))
    df['STOCK_LOG_RETURN'] = df.groupby(by='NAME')['LOG_IND'].apply(pd.Series.diff).reset_index()['LOG_IND']
    df = df[['NAME', 'CTRY_OF_DOM_NAME', "BOURSE_NAME", 'DATE','STOCK_PCT_RETURN', 'STOCK_LOG_RETURN']]

    # making sure that all firms have data starting from the same date
    full_index = pd.DataFrame(product(df["NAME"].unique(), df["DATE"].unique()))
    full_index.columns = ["NAME", "DATE"]

    df = full_index.merge(df, how="left", on=['NAME', 'DATE'])

    return df

def AbnormalReturns(df_ret, df_ind,  market_dict, exchange_dict, training_start_date, training_end_date, ret_variable, ind_variable):

    df_ret = df_ret[df_ret["DATE"] != datetime.strptime(training_start_date, '%Y-%m-%d').date()]
    df_ind = df_ind[df_ind["DATE"] != datetime.strptime(training_start_date, '%Y-%m-%d').date()]

    # set the estimation window
    date_start = datetime.strptime(training_start_date, '%Y-%m-%d').date()
    date_end = datetime.strptime(training_end_date, '%Y-%m-%d').date()

    company_array = df_ret[['NAME', 'CTRY_OF_DOM_NAME', "BOURSE_NAME"]].drop_duplicates().values
    
    data_abnormal_returns = df_ret[(df_ret["DATE"] >= date_end)]
    data_abnormal_returns['NORMAL_RETURN'] = pd.NA

    for company_list in company_array:
        company, cntry, exchange = company_list
        
        
        print(company)
        print(cntry)
        print(exchange)
        
        if (market_dict[cntry] in ["MSCI WORLD U$"]):
            print(f"Skip {company} because invalid index")
            continue
        elif (market_dict[cntry] in ["NA"]):
            market = exchange_dict[exchange]
            print(market)

            
            if (market in ["NA", "MSCI WORLD U$"]):
                print(f"Skip {company} because invalid index")
                continue
            
        else:
            market = market_dict[cntry]
        
        est_data_comp = df_ret[(df_ret['NAME']==company) & (df_ret["DATE"] > date_start) & (df_ret["DATE"] < date_end)]
        est_data_ind = df_ind[(df_ind['NAME'] == market) & (df_ind['DATE'] > date_start) & (df_ind['DATE']< date_end)].reset_index(drop=True).set_index(est_data_comp.index)
        est_data_ind = sm.add_constant(est_data_ind)
        
        if  est_data_comp[ret_variable].isna().sum()>0:
            print(f"Company: {company} skipped because NAs")
            continue 
        
        reg = sm.OLS(est_data_comp[ret_variable], est_data_ind[['const', ind_variable]]).fit(cov_type="HC3")
        
        pred_data_ind = df_ind[(df_ind['NAME'] == market) & (df_ind['DATE'] >= date_end)].reset_index(drop=True)
        pred_data_ind = sm.add_constant(pred_data_ind)
        
        
        predicted = reg.predict(pred_data_ind[['const', ind_variable]])
        predicted.name = 'NORMAL_RETURN'
        predicted = predicted.set_axis(data_abnormal_returns.loc[data_abnormal_returns['NAME']== company, 'NORMAL_RETURN'].index)
        
        data_abnormal_returns.loc[data_abnormal_returns['NAME']== company, 'NORMAL_RETURN'] = predicted
    
    return data_abnormal_returns
    