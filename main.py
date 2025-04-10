from mcp.server.fastmcp import FastMCP

from src.NBER.tools.search import get_search_result

from src.decorator.timer import timeit
from src.utils.merge_list import merge_results
from src.utils.tiny import save


mcp = FastMCP(name="NBER-MCP")

@timeit
@mcp.tool(name="search")
def search(q_list: list) -> list:
    """
    Search from NBER, and return the result.

    Args:
        q_list (list): A list of search questions.

    Returns:
        The list of search results.

    Notes:
        The search keywords should be as precise as possible.
        If you only use China and Chinese as search terms,
        the search time is about an hour,
        which is what I have tried, and what we don't want to face.
    """
    search_result: list = []
    for q in q_list:
        print(f"开始检索{q}")
        search_result.append(get_search_result(q))
    results = merge_results(search_result)
    save(str(results))
    return results


if __name__ == "__main__":
    mcp.run(transport="stdio")
