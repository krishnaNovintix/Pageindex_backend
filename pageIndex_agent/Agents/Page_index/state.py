from typing import Optional, Literal
from pydantic import BaseModel, Field


class IndexInput(BaseModel):
    pdf_path: str = Field(..., description="Path to the PDF file to index")
    output_dir: str = Field(..., description="Directory where the index structure JSON will be saved")


class IndexOutput(BaseModel):
    success: bool
    structure_path: Optional[str] = Field(None, description="Path to the generated structure JSON")
    message: str


class RetrieveInput(BaseModel):
    pdf_path: str = Field(..., description="Path to the PDF file")
    structure_path: str = Field(..., description="Path to the pre-built structure JSON")
    query: str = Field(..., description="Query to retrieve relevant content for")
    top_k: int = Field(5, ge=1, description="Number of top nodes to retrieve")


class RetrieveOutput(BaseModel):
    query: str
    nodes_used: list[str]
    node_titles: list[str]
    thinking: str
    answer: str


class PageIndexState(BaseModel):
    operation: Literal["index", "retrieve"]
    index_input: Optional[IndexInput] = None
    retrieve_input: Optional[RetrieveInput] = None
    index_output: Optional[IndexOutput] = None
    retrieve_output: Optional[RetrieveOutput] = None
