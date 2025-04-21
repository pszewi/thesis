# file with user-defined functions
import pandas as pd
import pymupdf
import os
from re import search, findall
import traceback


def ExtractNameYear(series_names, input_dir, nlp_model):
    '''Extracts the first page of each document and checks the year of release.'''
    
    filename_year_dict = {}
    for row in series_names:
        company_name = row.lower().replace(" ", "_")
        
        if any(i in company_name for i in ("?", "|")):
            company_name = company_name.replace("?", "")
            company_name = company_name.replace("|", "")
        
        company_dir = input_dir + "/" + company_name      
        
        list_of_paths = [company_dir + f"/{file}" for file in os.listdir(company_dir)]
        
        
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
                with open("exceptions.log", "a") as logfile:
                    traceback.print_exc(file=logfile)
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
        
        
        for file in os.listdir(company_dir):    
            try:
                file_year = findall(r"_\d+|\d+", file)
                
                if "_2017" in file_year:
                    path = company_dir + f"/{file}"
                    filename_year_dict[company_name] = (file, path)
                else:
                    continue
                
                
            except Exception as e:
                with open("exceptions_filename.log", "a") as logfile:
                    traceback.print_exc(file=logfile)
                    logfile.write(rf"The company that the error occured on:{company_name}\n")
                    logfile.write(f"The file that the error occured on:{file}")
        
    return filename_year_dict    


def ExtractAllText(filename_dict, year_str, output_path):
    
    if not os.path.exists(output_path + "/" + year_str):
        os.makedirs(output_path + "/" + year_str)
    
    
    
    for key in filename_dict.keys():
        
        if os.path.exists(output_path + "/" + year_str + "/" + key + ".txt"):
            continue
    
        try:
            with pymupdf.open(filename_dict[key][1]) as doc:
                txt = [page.get_text() for page in doc]
            
            with open(output_path + "/" + year_str + "/" + key + ".txt", "w") as file:
                file.write(' '.join(txt))
                    
        except Exception as e:
            with open(output_path + "/" + year_str + "/" + "_exceptions_all_text.log", "a") as logfile:
                logfile.write(rf"The company that the error occured on:{key}\n")
                traceback.print_exc(file=logfile)
   
                    
                    