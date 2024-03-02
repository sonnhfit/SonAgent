
def summary_doc(text: str) -> str:
    SUMMARY_DOC = f"""
    You are an expert software engineer with expertise in summarizing and pulling out important sections of a text. 
    The following text is from discussions and is about Software Development. 
    Follow these steps: read the text, summarize the text, and identify key issues can be planned for implementation. 
    In your response include the summary and bullet points for the main ideas, steps, and key vocabulary.
    ### Text
    {text}
    """
    return SUMMARY_DOC

