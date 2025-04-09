import openai
import os
from dotenv import load_dotenv
import json
from autogen import AssistantAgent
import asyncio
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
import re


current_directory = os.path.dirname(os.path.abspath(__file__))

class Selector():

    def __init__(self):
        load_dotenv()
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        openai.api_key = OPENAI_API_KEY
        self.message = dict()



    async def Access_Autogen_openai(self, prompt: str) -> str:
        model_client = OpenAIChatCompletionClient(model="gpt-4o")
        agent = AssistantAgent("assistant", model_client=model_client)
        response = await agent.run(task=prompt) 
        await model_client.close()
        return response
    


    async def get_user_question(self):
        print("Please enter your question in natural language:")
        user_question = input()
        self.message['user_question'] = user_question
        schema_json = await self.schema_selector(user_question)
        return schema_json



    async def schema_selector(self, user_question):
        result={}
        dev_tables_json = os.path.join(current_directory, '..\data\mini_dev\llm\mini_dev_data\dev_20240627\dev_tables.json')
        with open(dev_tables_json, 'r') as file:
            json_data = json.load(file)
        DB_list = [db['db_id'] for db in json_data]
        with open("agents/prompts/schema_selector.txt", "r") as file:
            schema_selector_prompt = file.read()

        ################################ bot1 : schema Selector ###################################
        schema_selector_prompt = schema_selector_prompt.format(user_question=user_question, db_list=DB_list)  
        schema = await self.Access_Autogen_openai(schema_selector_prompt)  
        ##############################################################################################

        assistant_message = schema.messages[-1].content
        #print(assistant_message)
        match = re.search(r"\[\'(.*?)\'\]", assistant_message)
        selected_schema = match.group(1) if match else None
        selected_schema_data=[]
        #print(selected_schema)
        for db in json_data:
            if db['db_id'] == selected_schema:
                selected_schema_data.append(db)
                break
        #print(selected_schema_data)
        with open("agents/prompts/tables_selector.txt", "r", encoding='utf-8') as file:
            table_selector_prompt = file.read()

        ################################ bot2 : filter table and columns Selector ####################
        table_selector_prompt = table_selector_prompt.format(user_question=user_question, DB_Json=selected_schema_data)
        filtered_details = await self.Access_Autogen_openai(table_selector_prompt)
        ################################################################################################

        
        assistant_message = filtered_details.messages[1].content
        start_idx = assistant_message.find("json\n{") + 5 
        end_idx = assistant_message.find("\n}\n") + 2  
        
        json_block = assistant_message[start_idx:end_idx].strip()
        
        extracted_data = json.loads(json_block)
        result["filters"]=extracted_data
        result['schema']=selected_schema
        result['user_question']=user_question
        return result
        




# Main execution
if __name__ == "__main__":
    selector = Selector()

    # Run the asynchronous get_user_question method
    asyncio.run(selector.get_user_question())  # Run the async function within asyncio event loop
