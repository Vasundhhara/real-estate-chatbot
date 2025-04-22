import os
import base64
import httpx
from dotenv import load_dotenv
from supabase import create_client
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage,AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")

llm1 = ChatOpenAI(model="gpt-4.1")
llm2 = ChatOpenAI(model="gpt-4o-mini")
llm3 = ChatOpenAI(model="gpt-4o")


def get_history(query):
    history_list = supabase.table('messages').select('history_list').execute()
    if history_list.data:
        print("History data found")
        history_list = history_list.data[0]['history_list']
        history_list = eval(history_list)
        print(type(history_list))
    else:
        history_list = []
    print("History list:", history_list)
    return history_list

    # history= supabase.table('messages').select('author','text').execute()
    # history_list=[]
    # if history.data:
    #     for message in history.data:
    #         author_id= message['author']
    #         text= message['text']

    #         if author_id == 'bot':
    #             history_list.append(AIMessage(content=text))
    #         else:
    #             history_list.append(HumanMessage(content=text))
    # # else:
    # #     history_list.append(HumanMessage(content=query))
    # print(history_list)
    # return history_list

#get_history("What is the process of renting a property?")
    

def update_history(query,response,history_list):
    if history_list == []:
        history_list.append(HumanMessage(content=query))
        history_list.append(AIMessage(content=response))
        print(history_list)
        supabase.table('messages').insert({"author": "f47ac10b-58cc-4372-a567-0e02b2c3d479", "history_list":str(history_list)}).execute()
    else:
        history_list.append(HumanMessage(content=query))
        history_list.append(AIMessage(content=response))
        print(history_list)
        supabase.table('messages').update({"history_list": str(history_list)}).eq('author', "f47ac10b-58cc-4372-a567-0e02b2c3d479").execute()

    
# history_list = get_history("What is the minimum lease period in the US ?")
# update_history("Can the landlord change rent mid agreement ?", "Not usually, but it depends on the lease.", history_list)


def chain1(user_query, image_data):
    template1 = """
Detect visible issues in the property (e.g., water damage, mold, cracks, poor lighting,
broken fixtures).Provide troubleshooting suggestions, such as:
“You might need to contact a plumber.”
“This looks like paint peeling due to moisture—consider using the anti-damp
coating.”
"""
    message = HumanMessage(
    content=[
        {"type": "text", "text": template1},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
        },
    ],
)
    print("Invoking chain 1 now...")
    response = llm1.invoke([message])
    response = response.content
    #print(response)
    return response

def chain2(user_query):
    template2 = """
Handle frequently asked questions related to tenancy laws, agreements,
landlord/tenant responsibilities, and rental processes.
Give location-specific guidance if the user's city or country is provided.
Answer common questions like:
“How much notice do I need to give before vacating?”
“Can my landlord increase rent midway through the contract?”
“What to do if the landlord is not returning the deposit?”

Ask follow up questions if required.
"""
    
    prompt2=ChatPromptTemplate.from_messages([
    ("system","Answer the user's question based on the following template: \n {template}"),
    MessagesPlaceholder(variable_name="history_list"),
    ("human","{input}")
    ])

    chain2 = (
      prompt2
      | llm2
      )
    
    history_list= get_history(user_query)
    history_list = str(history_list)
    history_list = eval(history_list)
    print("Invoking chain 2 now...")

    response=chain2.invoke(
    {
        "template":template2,
        "history_list":history_list,
        "input":user_query
    }
)
    response=response.content

    update_history(user_query,response,history_list)

    return response


def chain3(user_query):
    template3 = """
Answer the user query. Ask follow up questions 
"""
    
    prompt3=ChatPromptTemplate.from_messages([
    ("system","Answer the user's question based on the following template: \n {template}"),
    MessagesPlaceholder(variable_name="history_list"),
    ("human","{input}")
    ])


    chain3 = (
      prompt3
      | llm3
      )
    
    history_list= get_history(user_query)
    history_list = str(history_list)
    history_list = eval(history_list)
    
    print("Invoking chain 3 now...")
    response=chain3.invoke(
    {
        "template":template3,
        "history_list":history_list,
        "input":user_query
    }
)
    #response= response.__dict__
    response=response.content

    update_history(user_query,response,history_list)

    return response


def classification(user_query):
  classification_template = """
 You are good at classifying the category of a question.
Given the user question below, classify it in the following categories using the following instructions:

<If the question is about Issue Detection & Troubleshooting in a property, classify the question as 'issue'>
<If the question is about Tenancy, property laws, classify it as 'faq'>
<If the question is about anything else, classify it as 'general'>
**Always output only the lowercase category name (either 'issue' or 'faq' or 'general')**.

Examples:
- "There's a leak in the kitchen sink" → issue
- "What are my rights as a tenant?" → faq
- "Is the landlord responsible for repairs?" → faq

<question>
{query}
</question>

Classification:
"""

  classification_prompt= PromptTemplate(
        #Replace with your prompt template
      template="Answer the user query based on the below examples and template.\n{template}\n User Query :\n {query} \n Answer the user query based on the examples.",
      input_variables=["query"],
      partial_variables={"template": classification_template},
      )
  classification_chain = (
      classification_prompt
      | llm3
      )
  classification = classification_chain.invoke({"query": str(user_query)})
  classification= classification.__dict__
  classification=classification['content']
  print(classification)
  return classification

def main(user_query, image_data= None):
    category=classification(user_query)
    if category.strip().lower() == 'issue':
        response = chain1(user_query,image_data)
      
    elif category.strip().lower() == 'faq':
        response = chain2(user_query)

    else:
        response = chain3(user_query)
    return response


# def generate_response(user_query, user_id, jwt_token, image_data=None):

#     #############################################################
#     template1 = """
# Detect visible issues in the property (e.g., water damage, mold, cracks, poor lighting,
# broken fixtures).Provide troubleshooting suggestions, such as:
# “You might need to contact a plumber.”
# “This looks like paint peeling due to moisture—consider using the anti-damp
# coating.”
# """

#     prompt1= PromptTemplate(
#         #Replace with your prompt template
#       template="Answer the user query based on the below examples and template.\n{template}\n User Query :\n {query} \n Answer the user query based on the {image_data}.",
#       input_variables=["query"],
#       partial_variables={"template": template1, "image_data": image_data},
#       )
    
#     chain1 = (
#       prompt1
#       | llm1
#       )
    

#     # image_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg"

#     # image_data = base64.b64encode(httpx.get(image_url).content).decode("utf-8")
# #     query = user_query

# #     message = HumanMessage(
# #     content=[
# #         {"type": "text", "text": f"Detect visible issues in the property.{query}"},
# #         {
# #             "type": "image_url",
# #             "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
# #         },
# #     ],
# # )
    
#     ##############################################################
#     template2 = """
# Handle frequently asked questions related to tenancy laws, agreements,
# landlord/tenant responsibilities, and rental processes.
# Give location-specific guidance if the user's city or country is provided.
# Answer common questions like:
# “How much notice do I need to give before vacating?”
# “Can my landlord increase rent midway through the contract?”
# “What to do if the landlord is not returning the deposit?”
# """

#     prompt2= PromptTemplate(
#         #Replace with your prompt template
#       template="Answer the user query based on the below examples and template.\n{template}\n User Query :\n {query} \n Answer the user query based on the examples.",
#       input_variables=["query"],
#       partial_variables={"template": template2},
#       )
#     chain2 = (
#       prompt2
#       | llm2
#       )
    
#     ##############################################################
#     template3 = """

# """

#     prompt3= PromptTemplate(
#         #Replace with your prompt template
#       template="Answer the user query based on the below examples and template.\n{template}\n User Query :\n {query} \n Answer the user query based on the examples.",
#       input_variables=["query"],
#       partial_variables={"template": template3},
#       )
#     chain3 = (
#       prompt3
#       | llm3
#       )
#     ###############################################################
#     classification_template = PromptTemplate.from_template(
#     """You are good at classifying the category of a question.
# Given the user question below, classify it in the following categories using the following instructions:

# <If the question is about Issue Detection & Troubleshooting in a property, classify the question as 'issue'>
# <If the question is about Tenancy, property laws, classify it as 'faq'>
# **Always output only the lowercase category name (either 'issue' or 'faq')**.

# Examples:
# - "There's a leak in the kitchen sink" → issue
# - "What are my rights as a tenant?" → faq
# - "Is the landlord responsible for repairs?" → faq

# <question>
# {query}
# </question>

# Classification:"""
# )


    #classification_chain = classification_template | ChatOpenAI() | StrOutputParser()

    #################################################################
    # def route(info):
    #   global general_flag
    #   general_flag=0
    #   classification = info["topic"].strip().lower()  # Ensure lowercase

    #   if classification == "issue":
    #       print("Issue Detection & Troubleshooting")
    #       return chain1
    #   elif classification == "faq":
    #       print("Tenancy FAQ")
    #       return chain2
    #   else:
    #       general_flag = 1
    #       print("general chain")
    #       return chain3
      
    # full_chain = {
    #     "topic": classification_chain,
    #     "query": lambda x: x["query"],
    #   } | RunnableLambda(route)

    # try:
    #   response= full_chain.invoke({"query": str(user_query)})
    #   response= response.__dict__
    #   response=response['content']
    #   if general_flag == 1:
    #     #print("Flow terminated due to general chain")
    #     #return None, general_flag
    #     return response, general_flag
    #   else:    
    #     print(response)
    #     return response,general_flag

    # except Exception as e:
    #   raise RuntimeError(f"Error in invoking full_chain: {e}")

