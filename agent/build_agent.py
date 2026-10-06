from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_classic.agents import AgentExecutor,create_react_agent
from config import GEMINI_API_KEY,GEMINI_CHAT_MODEL
from agent.tools import make_document_tool,make_memory_tool
from agent.prompt import react_prompt


TEMPERATURE=0.1
MAX_ITERATIONS=10
llm = ChatGoogleGenerativeAI(
    model=GEMINI_CHAT_MODEL,
    google_api_key=GEMINI_API_KEY,
    temperature=TEMPERATURE
)



def build_executor(client,set_id):          #iam making function because tools need the parameters which llm cant pass
    tools=[make_document_tool(client=client,set_id=set_id),make_memory_tool(client=client,set_id=set_id)]

    agent=create_react_agent(llm=llm,
                             tools=tools,
                             prompt=react_prompt)
    
    executor=AgentExecutor(agent=agent,
                           tools=tools,        
                           handle_parsing_errors=True,
                           trim_intermediate_steps=True,
                           max_iterations=MAX_ITERATIONS
                           )

    return executor
