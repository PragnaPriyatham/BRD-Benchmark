import asyncio
from dotenv import load_dotenv
import os
import sqlite3
import json
import re
import pandas as pd
import openai
from autogen import AssistantAgent
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient


current_directory = os.path.dirname(os.path.abspath(__file__))

class Master_Bot():

    def __init__(self):
        self.message = dict()
        '''
        print("Please enter your question in natural language:")
        user_question = input()
        print("Please enter your Evidence:")
        evidence = input()
        print("Please enter DB_ID:")
        db_id = input()
        
        # testing data

        # db_id = "california_schools"
        # user_question = "Rank schools by their average score in Writing where the score is greater than 499, showing their charter numbers."
        # evidence= "Valid charter number means the number is not null"

        db_id = "california_schools"
        user_question = "Give the names of the schools with the percent eligible for free meals in K-12 is more than 0.1 and test takers whose test score is greater than or equal to 1500?"
        evidence= "VPercent eligible for free meals = Free Meal Count (K-12) / Total (Enrollment (K-12)"

        '''

        output_path = './mini_dev/llm/exp_result/masterbot/masterbot_predict_mini_dev_gpt_4_sqlite.json'


        with open('./mini_dev/llm/mini_dev_data/minidev/MINIDEV/mini_dev_sqlite.json', 'r') as f:
            dev_data = json.load(f)
        try:
            with open(output_path, 'r') as f:
                output = json.load(f)
        except FileNotFoundError:
            output = {}
        
        # Loop through dev data and feed it into your evaluator
        for idx,input in enumerate(dev_data):
            if idx < 88:
                continue  
            db_id = input['db_id']
            question = input['question']
            evidence = input.get('evidence', '')  # Handle missing evidence if any


            self.message['user_question'] = question
            self.message['evidence'] = evidence
            self.message['db_id'] = db_id
            final_sql=asyncio.run(self.start())
            formatted = f"{final_sql}\t----- bird -----\t{db_id}"
            output[str(idx)] = formatted
            with open(output_path, 'w') as f:
                json.dump(output, f, indent=4)



    async def Access_Autogen_openai(self, prompt):
            load_dotenv()
            OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
            openai.api_key = OPENAI_API_KEY
            model_client = OpenAIChatCompletionClient(model="gpt-4-turbo")
            agent = AssistantAgent("assistant", model_client=model_client)
            response = await agent.run(task=prompt) 
            await model_client.close()
            return response


        
    async def start(self):
        
        self.message['filters'] = await self.selector()
        schema=self.message['db_id']
        Selected_details_filters= json.loads(self.message['filters'])
        df_table_details={}
        table_details_path= os.path.join(current_directory, 'mini_dev\llm\mini_dev_data\minidev\MINIDEV\dev_databases',self.message['db_id'],'database_description')
        for table in Selected_details_filters.items():
            filename=table[0]+'.csv'
            tablepath = os.path.join(table_details_path, filename)
            df_table_details[table[0]]= pd.read_csv(tablepath, encoding='ISO-8859-1')
        print(self.message)
       
        Query_generated = await self.decomposer()
        Query_generated = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', Query_generated)
        Query_generated = json.loads(Query_generated)
        print(Query_generated)

        results = self.execute_sql(Query_generated['query'])
        print(results)
        if 'data' not in results or results['data'] ==[]:
            Query_generated = await self.refiner(results,df_table_details)
            Query_generated = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', Query_generated)
            Query_generated = json.loads(Query_generated)
            print(Query_generated)
            results = self.execute_sql(Query_generated['query'])
        print("This is FINAL Query")
        print(results)


        return results['sql']
        
    def execute_sql(self,Query_generated):
        schema=self.message['db_id']
        dev_sqlite= os.path.join(current_directory, 'mini_dev\llm\mini_dev_data\minidev\MINIDEV\dev_databases',schema)
        filename=schema+'.sqlite'
        db_path = os.path.join(dev_sqlite, filename)
        print("executing this query in sql")
        print(Query_generated)
        ## extablish connection ##
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
            
        try:
            cursor.execute(Query_generated)
            result = cursor.fetchall()
            return {
                "sql": str(Query_generated),
                "data": result[:5],
                "sqlite_error": "",
                "exception_class": ""
            }
        except sqlite3.Error as er:
            return {
                "sql": str(Query_generated),
                "sqlite_error": str(' '.join(er.args)),
                "exception_class": str(er.__class__)
            }
        except Exception as e:
            return {
                "sql": str(Query_generated),
                "sqlite_error": str(e.args),
                "exception_class": str(type(e).__name__)
            }
        finally:
            connection.close()



    

    def selected_schema_data(self):
        db_id=self.message['db_id'] 
        dev_tables_json = os.path.join(current_directory, 'mini_dev\llm\mini_dev_data\minidev\MINIDEV\dev_tables.json')
        with open(dev_tables_json, 'r') as file:
            json_data = json.load(file)
    
        selected_schema_data=None
        for db in json_data:
            if db['db_id'] == db_id:
                selected_schema_data = {
                    "db_id": db["db_id"],
                    "table_names_original": db["table_names_original"],
                    "column_names_original": db["column_names_original"]
                }

                return selected_schema_data



    async def selector(self):
        user_question=self.message['user_question'] 
        selected_schema_data=self.selected_schema_data()
        with open("agents/prompts/tables_selector.txt", "r", encoding='utf-8') as file:
            table_selector_prompt = file.read()

        ################################ Agent 1 : filter table and columns Selector ####################
        print("\033[0;34mAgent 1: Table selector in action\033[0m")
        table_selector_prompt = table_selector_prompt.format(user_question=user_question, DB_Json=selected_schema_data,evidence=self.message['evidence'])
        filtered_details = await self.Access_Autogen_openai(table_selector_prompt)
        ################################################################################################

        filtered_details = filtered_details.messages[1].content
        match = re.search(r'({.*})', filtered_details, re.DOTALL)
        filtered_details=match.group(1)
        return filtered_details

    
    async def decomposer(self):
        user_question=self.message['user_question']
        schema=self.message['db_id']
        schema_data=self.message['filters']
        prompt_path: str = "agents/prompts/decomposer.txt"
        with open(prompt_path, "r") as file:
            decomposer_prompt = file.read()

        ################################ Agent 2 : Decomposer Bot ###################################
        print("\033[0;34mAgent 2: Decomposer in action\033[0m")
        decomposer_prompt = decomposer_prompt.format(user_question=user_question,schema=schema,schema_data=schema_data,evidence=self.message['evidence'])
        decomposed_response = await self.Access_Autogen_openai(decomposer_prompt)
        ##############################################################################################

        decomposed_response = decomposed_response.messages[1].content
        match = re.search(r'({.*})', decomposed_response, re.DOTALL)
        decomposed_response=match.group(1)
        return decomposed_response

    async def refiner(self,results,db_details):
        user_question=self.message['user_question']
        prompt_path: str = "agents/prompts/refiner.txt"
        with open(prompt_path, "r") as file:
            refiner_prompt = file.read()
        ################################ Agent 3 : Refiner Bot ###################################
        print("\033[0;34mAgent 3: Refiner in action\033[0m")
        refiner_prompt = refiner_prompt.format(user_question=user_question,Query=results['sql'],error=results['sqlite_error'],db_details=db_details,evidence=self.message['evidence'])
        refined_query = await self.Access_Autogen_openai(refiner_prompt)
        ###########################################################################################

        refined_query = refined_query.messages[1].content
        match = re.search(r'({.*})', refined_query, re.DOTALL)
        refined_query=match.group(1)
        return refined_query



if __name__ == "__main__":
    bot = Master_Bot()