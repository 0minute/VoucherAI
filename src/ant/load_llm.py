from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import OpenAIEmbeddings

from dotenv import load_dotenv
import warnings
import os
from src.utils.constants import ROOT_DIR

warnings.filterwarnings('ignore')
load_dotenv(dotenv_path = os.path.join(ROOT_DIR, "src", "ant", ".env"))
os.environ["OPENAI_API_KEY"] = os.getenv('OPENAI_API_KEY')
HOST = os.getenv('HOST')
PORT = os.getenv('PORT')
PORT2 = os.getenv('PORT2')
EMBED_PORT = os.getenv('EMBED_PORT')

def get_available_models():
    """사용 가능한 모델 목록을 반환합니다."""
    return {
        "gpt4o_latest": {
            "model": "openai.gpt-4o-2024-11-20",
            "memo": "최신 4o 모델, 이미지+텍스트 멀티모달 처리와 추론 균형이 뛰어나 OCR 교차검증과 정리에 최적"
        },
        "gpt4o_latest_mini": {
            "model": "openai.gpt-4o-mini",
            "memo": "최신 4o-mini 모델, 속도/효율"
        },
        "gpt41_latest": {
            "model": "openai.gpt-4.1-2025-04-14",
            "memo": "복잡한 규칙 기반 추론과 데이터 정합성 유지에 강함, 고난이도 문서 정리에 적합"
        },
        "claude37s": {
            "model": "bedrock.anthropic.claude-3-7-sonnet-v1",
            "memo": "긴 문맥과 정교한 지시 따르기에 강하며, 대용량 OCR 텍스트 구조화 품질 우수"
        },
        "gemini25p": {
            "model": "vertex_ai.gemini-2.5-pro",
            "memo": "네이티브 멀티모달 이해력 우수, 표/레이아웃 해석에 강하며 GCP 환경 운영 시 유리"
        },
        "gpt41m_latest": {
            "model": "openai.gpt-4.1-mini-2025-04-14",
            "memo": "가성비 좋은 추론용 모델, 대량 트래픽 상황에서 요약·키밸류 추출에 적합"
        },
        "embed3l": {
            "model": "openai.text-embedding-3-large",
            "memo": "검색·유사도·클러스터링 품질 우수, OCR 텍스트 근거 검색 및 중복 제거에 활용"
        },
        "cohere_rerank": {
            "model": "bedrock.cohere.rerank-3-5",
            "memo": "유사도 검색 결과에서 근거 문장 우선순위 정렬 품질이 뛰어나 필드 충돌 시 유용"
        }
    }



def load_llm_model(model_name: str):
    selected_model = get_available_models()[model_name]
    openai_api_base = "https://genai-sharedservice-americas.pwcinternal.com"
    llm = ChatOpenAI(
            model=selected_model["model"],
            openai_api_base=openai_api_base,
            max_tokens=4000,
            temperature=0.7,
            top_p=0.8,
        )

    return llm