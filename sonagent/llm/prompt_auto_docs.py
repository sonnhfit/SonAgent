def auto_skill_docs(code: str) -> str:
    SYSTEM_PROMP = (
        "You are a software engineer with the ability to write " +
        "Python software documentation. "
        "You receive an INPUT and document that code in OUTPUT."
    )

    AUTO_DOCS_PROMP = """

        document  INPUT code with document template like example
        Example 1:
        
[INPUT]
```python
import sys
from typing import TYPE_CHECKING, List, Optional

if sys.version_info >= (3, 9):
    from typing import Annotated
else:
    from typing_extensions import Annotated

from semantic_kernel.functions.kernel_function_decorator import kernel_function

if TYPE_CHECKING:
    from semantic_kernel.connectors.search_engine.connector import ConnectorBase


class WebSearchEnginePlugin:

    _connector: "ConnectorBase"

    def __init__(self, connector: "ConnectorBase") -> None:
        self._connector = connector

    @kernel_function(description="Performs a web search for a given query")
    async def search(
        self,
        query: Annotated[str, "The search query"],
        num_results: Annotated[Optional[int], "The number of search results to return"] = 1,
        offset: Annotated[Optional[int], "The number of search results to skip"] = 0,
    ) -> List[str]:
        return await self._connector.search(query, num_results, offset)
```
[OUTPUT]
Description: A plugin that provides web search engine functionality

Usage:
    connector = BingConnector(bing_search_api_key)
    kernel.import_plugin_from_object(WebSearchEnginePlugin(connector), plugin_name="WebSearch")

Examples:
    {{WebSearch.search "What is semantic kernel?"}}
    =>  Returns the first `num_results` number of results for the given search query
        and ignores the first `offset` number of results.

Method:
    - `search(query: str, num_results: Optional[int] = 1, offset: Optional[int] = 0) -> List[str]`:
        Performs a web search for a given query and returns a list of search results.

    - `__init__(connector: ConnectorBase)`:
        Initializes the plugin with the specified connector.


[INTPUT]
```python
{code}
```
[OUTPUT]
"""
    return SYSTEM_PROMP, AUTO_DOCS_PROMP.format(code=code)
