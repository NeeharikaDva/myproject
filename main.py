def api_test(request):
    from google.cloud import storage
    from google.cloud import bigquery 
    from google.cloud.exceptions import NotFound
    import ast
    import pandas as pd
    import json
    import requests
    import re

    bucket_name = 'bucket1_api1'
    variables_file_name = 'apitemp2.txt'


    #Establishing the connection to different GCP resources---Accessing variables_dictionary_file and extracting dictionary of variables from it 
    storage_client = storage.Client()
    bucket = storage_client.get_bucket(bucket_name)
    blob = bucket.blob(variables_file_name)
    b=blob.download_as_string()
    # Now we have a bytes string, convert that into a stream
    dict_str = b.decode("UTF-8")
    Variables_dict = ast.literal_eval(dict_str)

    api_link=Variables_dict['api_link']
    print(Variables_dict['api_link'])
    gcpprojectname=Variables_dict['gcpprojectname']
    print(Variables_dict['gcpprojectname'])
    dataset_name=Variables_dict['dataset_name']
    print(Variables_dict['dataset_name'])
    bucket_name=Variables_dict['bucket_name']
    print(Variables_dict['bucket_name'])
    uri=Variables_dict['uri']
    print(Variables_dict['uri'])
    gcs_folder_name=Variables_dict['gcs_folder_name']
    print(Variables_dict['gcs_folder_name'])
    filename=Variables_dict['filename']
    print(Variables_dict['filename'])

    response = requests.get(api_link)
    response.raise_for_status()
    json_data=response.json()

    # set the filename of your json object
    json_object = json_data

    def create_json(json_object, filename):
        '''
        this function will create json object in
        google cloud storage
        '''
        # create a blob
        blob = bucket.blob("{}/{}".format(gcs_folder_name,filename))
        #blob = bucket.blob(filename)
        # upload the blob 
        blob.upload_from_string(
            data=json.dumps(json_object),
            content_type='application/json'
        )
        result = filename + ' upload complete'
        return {'response' : result}

    print("file created successfully")

    create_json(json_object, filename)

    storage_client = storage.Client()
    bigquery_client = bigquery.Client(project=gcpprojectname)


    #Function to create a dataset in Bigquery
    def bq_create_dataset(bigquery_client, dataset):
        dataset_ref = bigquery_client.dataset(dataset)
            #print(dataset_ref)
        try:
            dataset = bigquery_client.get_dataset(dataset_ref)
                #print(dataset)
            print('Dataset {} already exists.'.format(dataset.dataset_id))
            return f'Dataset {dataset} already exists.'
        except NotFound:
            dataset = bigquery.Dataset(dataset_ref)
                #print(dataset)
            dataset.location = 'us-central1'
            dataset = bigquery_client.create_dataset(dataset)
            print('Dataset {} created.'.format(dataset.dataset_id))
            return dataset


    bq_create_dataset(bigquery_client,dataset_name)

    def gcs_to_bq():    
        for blob in bucket.list_blobs(prefix = gcs_folder_name):
            if blob.name.endswith('json'):
                filename = re.findall(r".*/(.*).json",blob.name) #Extracting file name for BQ's table id
                filenametest=filename[0].strip().replace(" ", "")
                print(filenametest)
                table_id = f'{gcpprojectname}.{dataset_name}.{filenametest}' # Determining table name
                print(table_id)
                temp=blob.name
                uri1= "gs://{}".format(bucket_name)
                uri =f'{uri1}/{temp}'
                print(uri)
                df=pd.read_json(uri)
                df.to_csv(uri,index=False)


                #destination_tables_list.append(filenametest)   #extracting the destination table names
            job_config = bigquery.LoadJobConfig(
                autodetect=True,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            )     
            load_job = client.load_table_from_dataframe(
                df,
                table_id,
                location="us-central1",   # Must match the destination dataset location.
                job_config=job_config,
            )  # Make an API request.
            load_job.result()
            destination_table = client.get_table(table_id)
            print("Loaded {} rows.".format(destination_table.num_rows))         
                  
    gcs_to_bq()
   
    return 'success'


