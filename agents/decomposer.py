import openai
import os
from dotenv import load_dotenv
from autogen import AssistantAgent
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient
import asyncio

# Load environment variables
load_dotenv()

# Define Decomposer class
class Decomposer():
    def __init__(self):
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
        openai.api_key = OPENAI_API_KEY

    async def Access_Autogen_openai(self, prompt: str) -> str:
        """
        Accesses the OpenAI API through the AssistantAgent to get the model's response
        """
        model_client = OpenAIChatCompletionClient(model="gpt-4o")
        agent = AssistantAgent("assistant", model_client=model_client)
        response = await agent.run(task=prompt) 
        await model_client.close()
        return response

    async def decomposer(self,Selected_details):
        """
        Reads the decomposer prompt from the file and sends it to the OpenAI model for processing.
        """
        
        user_question=Selected_details['user_question']
        schema=Selected_details['schema']
        schema_data=Selected_details['filters']
        try:
            prompt_path: str = "agents/prompts/decomposer.txt"
            with open(prompt_path, "r") as file:
                decomposer_prompt = file.read()
            ################################ bot3 : Decomposer Bot ###################################
            decomposer_prompt = decomposer_prompt.format(user_question=user_question,schema=schema,schema_data=schema_data)
            decomposed_response = await self.Access_Autogen_openai(decomposer_prompt)
            ##############################################################################################
            Query = decomposed_response.messages[-1].content
            Query=Query.split("Final Query")[-1].strip()
            Query = Query.split("```sql")[-1].strip().split(';')[0]
            return Query

        except Exception as e:
            return f"Error in decomposing the question: {str(e)}"
