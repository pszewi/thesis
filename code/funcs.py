# file with user-defined functions
import pandas as pd
import pymupdf
from os import listdir, makedirs
from os.path import exists
from re import search, findall
from traceback import print_exc
from json import dump, load


def ExtractNameYear(series_names, input_dir, nlp_model):
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
                    
                    if "2017" in num:
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



def ExtractFileName(series_names, input_dir):
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
                
                if "_2017" in file_year:
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
    for out in pipe(sentences, padding=True, truncation=True):
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
        green_ind = num_non_spec/num_clim_related  
        
        clim_related_nums.append(num_clim_related)  
        non_spec_nums.append(num_non_spec)
        green_inds.append(green_ind)
    
    df = pd.DataFrame({"NAME":series_name, 
                       'CLIMATE_REL':clim_related_nums, 
                       "NON_SPEC":non_spec_nums,
                       "GREEN_IND":green_inds
                       })
    
    return df
        
            
        
    