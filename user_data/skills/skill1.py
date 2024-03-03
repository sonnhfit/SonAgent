from semantic_kernel.sk_pydantic import SKBaseModel
from semantic_kernel.orchestration.sk_context import SKContext
from semantic_kernel.skill_definition import sk_function, sk_function_context_parameter
import numpy as np
from pydantic import BaseModel


# from sonagent.skills.skills import SonSkill

class MathSkill(BaseModel):
    """
    Description: MathSkill provides a set of functions to make Math calculations.

    Usage:
        kernel.import_skill(MathSkill(), skill_name="math")

    Examples:
        {{math.Add}}         => Returns the sum of initial_value_text and Amount (provided in the SKContext)
    """

    def name(self) -> str:
        return "MathSkill"

    @sk_function(
        description="Adds value to a value",
        name="Add",
        input_description="The value to add",
    )
    @sk_function_context_parameter(
        name="initial_value",
        description="value init",
        required=True,
    )
    @sk_function_context_parameter(
        name="amount",
        description="Amount to add",
        required=True,
    )
    def add(self, initial_value: int, amount: int, context: "SKContext") -> str:
        """
        Returns the Addition result of initial and amount values provided.

        :param initial_value: Initial value as string to add the specified amount
        :param context: Contains the context to get the numbers from
        :return: The resulting sum as a string
        """
        return initial_value + amount

    @sk_function(
        description="Multiplies value by a factor",
        name="Multiply",
        input_description="The value to multiply",
    )
    @sk_function_context_parameter(
        name="value",
        description="The value to be multiplied",
        required=True,
    )
    @sk_function_context_parameter(
        name="factor",
        description="The factor to multiply by",
        required=True,
    )
    def multiply(self, value: int, factor: int, context: "SKContext") -> str:
        """
        Returns the multiplication result of value and factor.

        :param value: The value to be multiplied
        :param factor: The factor to multiply by
        :param context: Contains the context to get the numbers from
        :return: The resulting product as a string
        """
        return value * factor
    
    
class SummarySkill(BaseModel):
    """
    Description: SummarySkill provides a set of functions to summarize text.
    """
    def name(self) -> str:
        return "SummarySkill"
    
    
    

