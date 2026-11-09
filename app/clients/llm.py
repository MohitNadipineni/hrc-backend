from app.core.config import settings


def chat(system: str, user: str) -> str:
    from langchain_openai import AzureChatOpenAI

    model = AzureChatOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        azure_deployment=settings.azure_chat_deployment,
        temperature=0,
    )
    reply = model.invoke([("system", system), ("human", user)])
    return reply.content