from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2:3b")
response = llm.invoke("Reply with exactly: setup works")
print(response.content)
