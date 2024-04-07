
#to do: move this one to langchain 


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


def create_git_pull_request_param(sumary_text):

    GITHUB_PULL_REQUEST = f"""
    You are a software engineer working on a python project.
    You have been asked to create a pull request for the following changes.
    The changes are to the codebase of a project. 
    Based on the content provided below. Let's create a json file, ouput is json.

    For example:

    Example 1:
    ### SUMMARY
    SonAgent (to assistant):
    create a python class that have function to plot apple stock price in from 1 year ago to now user yahoo finance data 
    that class need extend from 
    ```python
    from pydantic import BaseModel
    ```
    --------------------------------------------------------------------------------
    assistant (to SonAgent):

    To accomplish this task, we will create a Python class that extends from `BaseModel` provided by `pydantic`. This class will have a function to plot the Apple stock price from 1 year ago to the current date using Yahoo Finance data. We will use the `yfinance` library to fetch the stock data and `matplotlib` for plotting. If you don't have `yfinance` and `matplotlib` installed, you will need to install them using pip.

    Here's the plan:
    1. Import necessary libraries.
    2. Extend the class from `BaseModel`.
    3. Implement a function within the class to fetch and plot the Apple stock price data.

    First, ensure you have `pydantic`, `yfinance`, and `matplotlib` installed. You can install them using pip. Execute the following command in your shell:

    ### OUTPUT
    {
        "branch_name": "feature/sonagent-plot-apple-stock",
        "commit_message": "add new feature to plot apple stock price",
        "pull_request_title": "Add new skill to agent to plot Apple stock price",
        "pull_request_body": "This pull request adds a new skill to the agent to plot the Apple stock price using Yahoo Finance data.",
        "source_code_file_name": "skill_plot_apple_stock.py",
    }

    Example 2:
    ### SUMMARY
    Certainly! The following is a summary of the Python function for performing a Google search using the googlesearch-python library:
    Install the googlesearch-python library using pip install googlesearch-python.
    Create a function called google_search that takes a search query and an optional parameter for the number of results to fetch.
    Inside the function, use the search function from the library to perform the Google search with the given query and retrieve the specified number of results.
    Iterate through the search results and print the title and URL of each result.
    Handle exceptions gracefully in case of errors during the search process.
    Remember to use this functionality responsibly and be aware of potential legal and ethical considerations when interacting with external APIs or web services.

    ### OUTPUT
    {
        "branch_name": "feature/sonagent-google-search",
        "commit_message": "add new feature to perform Google search",
        "pull_request_title": "Add new skill to agent to perform Google search",
        "pull_request_body": "This pull request adds a new skill to the agent to perform a Google search using the googlesearch-python library.",
        "source_code_file_name": "skill_google_search.py",
    }


    ### SUMMARY
    {sumary_text}

    ### OUTPUT

    """

    return GITHUB_PULL_REQUEST



GITHUB_PULL_REQUEST_PROMPT = """
You are a software engineer working on a python project.
You have been asked to create a pull request for the following changes.
The changes are to the codebase of a project. 
Based on the content provided below. Let's create a json file, ouput is json that format can load by json.loads.

For example:

Example 1:
[SUMMARY]
SonAgent (to assistant):
create a python class that have function to plot apple stock price in from 1 year ago to now user yahoo finance data 
that class need extend from 
```python
from pydantic import BaseModel
```
--------------------------------------------------------------------------------
assistant (to SonAgent):

To accomplish this task, we will create a Python class `PlotAppleStock` that extends from `BaseModel` provided by `pydantic`. 
This class will have a function to plot the Apple stock price from 1 year ago to the current date using Yahoo Finance data. 
We will use the `yfinance` library to fetch the stock data and `matplotlib` for plotting. 
If you don't have `yfinance` and `matplotlib` installed, you will need to install them using pip.

Here's the plan:
1. Import necessary libraries.
2. Extend the class from `BaseModel`.
3. Implement a function within the class to fetch and plot the Apple stock price data.

First, ensure you have `pydantic`, `yfinance`, and `matplotlib` installed. You can install them using pip. Execute the following command in your shell:

[OUTPUT]
```json
{{
    "branch_name": "feature/sonagent-plot-apple-stock",
    "commit_message": "add new feature to plot apple stock price",
    "pull_request_title": "Add new skill to agent to plot Apple stock price",
    "pull_request_body": "This pull request adds a new skill to the agent to plot the Apple stock price using Yahoo Finance data.",
    "source_code_file_name": "skill_plot_apple_stock.py",
    "class_name": "PlotAppleStock"
}}
```

Example 2:
[SUMMARY]
Certainly! The following is a summary of the Python function for performing a Google search using the googlesearch-python library:
Install the googlesearch-python library using pip install googlesearch-python.
Create a class called `GooleSearch` have a function called google_search that takes a search query and an optional parameter for the number of results to fetch.
Inside the function, use the search function from the library to perform the Google search with the given query and retrieve the specified number of results.
Iterate through the search results and print the title and URL of each result.
Handle exceptions gracefully in case of errors during the search process.
Remember to use this functionality responsibly and be aware of potential legal and ethical considerations when interacting with external APIs or web services.

[OUTPUT]
```json
{{
    "branch_name": "feature/sonagent-google-search",
    "commit_message": "add new feature to perform Google search",
    "pull_request_title": "Add new skill to agent to perform Google search",
    "pull_request_body": "This pull request adds a new skill to the agent to perform a Google search using the googlesearch-python library.",
    "source_code_file_name": "skill_google_search.py",
    "class_name": "GooleSearch"
}}
```

[SUMMARY]
{sumary_text}

[OUTPUT]

"""


def rewrite_code_with_docstring(input_code: str) -> str:
    ADD_DOCSTRING_TO_CLASS = f'''
You are a software engineer working on a Python project. You need to add  or rewrite docs string to Python classes following the following rules:
- Classes must have docstrings listing all the parameters of a function, as shown in the example
- If the function call to execute the code is not placed within the if name == "main": block, please move the code execution into the if name == "main": block. This is because this code block is intended for use when importing into other modules
- Please note that the syntax for the class docs string should follow the format as follows: ClassName.function_name after that followed by a description of the function's parameters in the args section
- if source code not have class, you need to create a class and move the function into the class that class need to extend from `BaseModel` provided by `pydantic`
- function inside a class need self as first argument
- keep import statement at the top of the file dont remove import becauset that will make code wrong
### example 1
[INPUT]

```python
from pydantic import BaseModel

class NumberPrinter(BaseModel):
    def print_numbers(self, start, end):
        rs = ""
        for i in range(start, end + 1):
            rs += str(i) + " "
        return rs

# Example usage
if __name__ == "__main__":
    printer = NumberPrinter()
    printer.print_numbers()
```

[OUTPUT]

```python
from pydantic import BaseModel

class NumberPrinter(BaseModel):
    """
    NumberPrinter.print_numbers
    description: print from start to end
    args:
        start: int start number
        end: int end number
    """

    def print_numbers(self, start, end):
        # print number from start to end
        rs = ""
        for i in range(start, end + 1):
            rs += str(i) + " "
        return rs

# Example usage
if __name__ == "__main__":
    printer = NumberPrinter()
    printer.print_numbers()
```

### example 2
[INPUT]
```python
# filename: apple_stock_plotter.py
from pydantic import BaseModel
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class GetAppleStockPlotter(BaseModel):

    def stock_price(self):
        # Calculate the date 1 year ago from today
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        apple_stock_data = yf.download('AAPL', start=start_date_str, end=end_date_str)
        return str(apple_stock_data['Close'][-1])

    def plot_stock(self, plot_days=30):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=plot_days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        apple_stock_data = yf.download('AAPL', start=start_date_str, end=end_date_str)
        apple_stock_data['Close'].plot(title="Apple Stock Price")
        plt.show()
```

[OUTPUT]

```python
# filename: apple_stock_plotter.py
from pydantic import BaseModel
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

class GetAppleStockPlotter(BaseModel):
    """
    GetAppleStockPlotter.stock_price
    description: get latest Apple stock price from yahoo finace.
    args:

    ----
    GetAppleStockPlotter.plot_stock
    description: plot the latest Apple stock price from yahoo finace.
    args:
        plot_days: int number of days to plot
    
    """
    def stock_price(self):
        # Calculate the date 1 year ago from today
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        apple_stock_data = yf.download('AAPL', start=start_date_str, end=end_date_str)
        return str(apple_stock_data['Close'][-1])

    def plot_stock(self, plot_days=30):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=plot_days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        apple_stock_data = yf.download('AAPL', start=start_date_str, end=end_date_str)
        apple_stock_data['Close'].plot(title="Apple Stock Price")
        plt.show()
```
[INPUT]
```python
{input_code}
```
[OUTPUT]

    '''

    return ADD_DOCSTRING_TO_CLASS


DEFAULT_SYSTEM_MESSAGE_AUTO_GEN = """You are a helpful AI assistant.
Solve tasks using your coding and language skills.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
When you find an answer, verify the answer carefully. Include verifiable evidence in your response if possible.
Reply "TERMINATE" in the end when everything is done.

follow coding conventions and best practices bellow:
- Classes must have docstrings, keep docs string of class and function what you get
- If the function call to execute the code is not placed within the if name == "main": block, please move the code execution into the if name == "main": block. This is because this code block is intended for use when importing into other modules
- Please note that the syntax for the class docs string should follow the format as follows: ClassName.function_name after that followed by a description of the function's parameters in the args section
- if source code not have class, you need to create a class and move the function into the class that class need to extend from `BaseModel` provided by `pydantic`
- function inside a class need self as first argument
- keep import statement at the top of the file dont remove import becauset that will make code wrong
- For IO operations when required to print or notify the user, use the following method instead of the print function `from sonagent.rpc import IOMsg` IOMsg.send_msg(text) with text is str type message you want to send, or print 
- For Input operations when required to get input from the user, use the following method instead of the input function `from sonagent.rpc import IOMsg` IOMsg.get_input() and store the result in a variable, dont use input function
    """
