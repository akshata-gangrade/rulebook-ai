from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """
    Request body for the /ask endpoint.
    """

    question: str = Field(
        min_length=1,
        description="Question to ask about the university rulebook.",
    )