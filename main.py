import asyncio
from agents.selector import Selector  
from agents.decomposer import Decomposer
import os
import sqlite3


current_directory = os.path.dirname(os.path.abspath(__file__))

class Master_Bot():

    def __init__(self):
        self.message = dict()

    async def start(self):
        '''
        selector = Selector()
        Selected_details = await selector.get_user_question()

        #test data
        #Selected_details={'filters': {'gender': 'keep_all', 'superhero': ['superhero name', 'gender id', 'weight kg', 'id', 'race id', 'height cm'], 'attribute': 'drop_all', 'hero attribute': 'drop_all', 'alignment': 'drop_all', 'superpower': 'drop_all', 'hero power': 'drop_all', 'colour': 'drop_all', 'publisher': 'drop_all', 'race': 'drop_all'}, 'schema': 'superhero', 'user_question': 'Among the male superheroes, list the super hero names of superheroes with weight greater than the 79% average weight of all superheroes.'}
        
        decomposer = Decomposer()
        Query_generated = await decomposer.decomposer(Selected_details) 
        schema = Selected_details['schema']
        '''

        #test data
        Query_generated="SELECT (SELECT COUNT(*) FROM superhero WHERE height_cm BETWEEN 150 AND 180 AND publisher_id = 1) * 100.0 / (SELECT COUNT(*) FROM superhero WHERE height_cm BETWEEN 150 AND 180) AS marvel_percentage"
        schema="superhero"

       
        results=self.execute_sql(Query_generated,schema)
        for result in results:
            print(result)



    def execute_sql(self,Query_generated,schema):

        dev_sqlite= os.path.join(current_directory, 'data\mini_dev\llm\mini_dev_data\dev_20240627\dev_databases\dev_databases',schema)
        filename=schema+'.sqlite'
        db_path = os.path.join(dev_sqlite, filename)

        ## extablsh connection ##
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.execute(Query_generated)
        results = cursor.fetchall()
        connection.close()

        return results

if __name__ == "__main__":
    master_bot = Master_Bot()
    asyncio.run(master_bot.start()) 