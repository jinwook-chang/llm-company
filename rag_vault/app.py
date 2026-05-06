import os
# Suppress LangChain deprecation warnings
os.environ["LANGCHAIN_ALLOW_DEPRECATION_WARNINGS"] = "true"

import streamlit as st
from agent_logic import create_agent
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import json

def format_message_content(content):
    """메시지 내용이 리스트나 딕셔너리 형태일 경우 텍스트만 추출합니다."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                texts.append(item["text"])
            elif isinstance(item, str):
                texts.append(item)
        return "".join(texts)
    return str(content)

st.set_page_config(page_title="Vault RAG 챗봇", page_icon="🗄️")

st.title("🗄️ Vault RAG 챗봇")
st.markdown("Vault 내의 지식 문서를 기반으로 답변을 제공합니다.")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 대화 기록 표시
for message in st.session_state.messages:
    with st.chat_message("user" if isinstance(message, HumanMessage) else "assistant"):
        st.markdown(format_message_content(message.content))

# 사용자 입력
if prompt := st.chat_input("Vault에 대해 궁금한 점을 물어보세요."):
    st.session_state.messages.append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        full_response = ""
        with st.status("Thinking...", expanded=True) as status:
            # 에이전트 생성
            agent = create_agent()
            
            # 에이전트 실행 (스트리밍 방식)
            for chunk in agent.stream({"messages": st.session_state.messages}):
                # 1. 도구 호출 확인
                if "agent" in chunk:
                    messages = chunk["agent"]["messages"]
                    for msg in messages:
                        if hasattr(msg, "tool_calls") and msg.tool_calls:
                            for tc in msg.tool_calls:
                                tool_name = tc["name"]
                                args = tc["args"]
                                display_input = args.get("query") or args.get("file_path") or str(args)
                                
                                if tool_name == "search_documents":
                                    st.markdown(f"🔍 **Vault 검색 중:** `{display_input}`")
                                elif tool_name == "read_documents":
                                    st.markdown(f"📖 **문서 읽는 중:** `{display_input}`")
                                else:
                                    st.markdown(f"🛠️ **{tool_name}** 실행 중: `{display_input}`")
                
                # 2. 최종 응답 확인
                for node_name, node_data in chunk.items():
                    if "messages" in node_data:
                        last_msg = node_data["messages"][-1]
                        if isinstance(last_msg, AIMessage) and not (hasattr(last_msg, "tool_calls") and last_msg.tool_calls):
                            full_response = last_msg.content
            
            status.update(label="Complete!", state="complete", expanded=False)
        
        # 포맷팅 후 출력
        formatted_response = format_message_content(full_response)
        st.markdown(formatted_response)
        st.session_state.messages.append(AIMessage(content=formatted_response))
