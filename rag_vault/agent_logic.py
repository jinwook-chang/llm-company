import os
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
from utils import get_model
from tools import get_tools

SYSTEM_PROMPT = """너는 Vault(지식 저장소) 분석 전문가 챗봇이야.
사용자의 질문에 대해 Vault 내의 문서들을 검색하여 답변을 제공해야 해.

작동 방식:
1. `search_documents` 도구를 사용하여 관련 문서를 먼저 검색해.
2. 검색된 결과 중 파일 경로를 확인하고, `read_documents` 도구를 사용하여 상세 내용을 읽어.
3. 질문에 충분히 답할 수 있을 때까지 검색과 읽기를 반복해 (Agentic RAG).
4. 답변 시에는 반드시 근거가 되는 문서명(파일 경로)을 인용하며 최대한 상세히 설명해.
5. 문서에서 찾을 수 없는 내용은 아는 척 하지 말고 정중히 모른다고 답변해.
6. 한국어로 답변해줘.
"""

def create_agent(user_id="default_user"):
    llm = get_model(user_id=user_id)
    tools = get_tools()

    # 에이전트 생성
    agent = create_react_agent(
        model=llm,
        tools=tools,
        prompt=SYSTEM_PROMPT,
    )

    return agent
