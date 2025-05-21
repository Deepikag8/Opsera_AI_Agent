from .base_tool import BaseTool
from typing import Dict, Any, Union

class CalculatorTool(BaseTool):
    """A tool for performing basic arithmetic calculations."""
    
    @property
    def name(self) -> str:
        return "calculator"
    
    @property
    def description(self) -> str:
        return "Performs basic arithmetic calculations. Input should be a single string expression like '5 + 3' or '10 * 2 / (4 - 2)'."
    
    def get_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The mathematical expression to evaluate (e.g., '5 + 3', '10 * 2 / 4')."
                }
            },
            "required": ["expression"]
        }
    
    def execute(self, expression: str) -> Union[float, str]:
        """Evaluates a mathematical expression string."""
        
        # Basic whitelist of allowed characters for the expression
        # This is a simple attempt to prevent arbitrary code execution with eval().
        # A more robust solution would be to use a proper math expression parser.
        allowed_chars = set("0123456789+-*/(). " + "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_" ) # Allow functions like pow, sqrt
        
        # Allow common math functions from the math module for the eval context
        # This is a safer alternative than importing everything from math
        import math
        safe_math_functions = {
            name: getattr(math, name) 
            for name in dir(math) 
            if callable(getattr(math, name)) and not name.startswith("__")
        }
        # Add common constants
        safe_math_functions['pi'] = math.pi
        safe_math_functions['e'] = math.e
        
        # Create a limited global scope for eval
        eval_globals = {
            "__builtins__": {},
            **safe_math_functions
        }

        if not expression.strip():
            return "Error: Empty expression provided."
        
        # Validate characters in expression more carefully
        # This regex allows numbers, operators, parentheses, spaces, and function names/constants (alphanumeric with underscore)
        import re
        if not re.match(r"^[a-zA-Z0-9\s_.\+\-\*/\(\)\^%]*$", expression):
             return f"Error: Expression '{expression}' contains invalid characters."

        try:
            # Replace ^ with ** for Python's exponentiation
            processed_expression = expression.replace('^', '**')

            # Evaluate the expression in a restricted environment
            result = eval(processed_expression, eval_globals, {})
            if isinstance(result, (int, float)):
                return float(result)
            else:
                # This case might occur if eval results in something unexpected (e.g. a function object if not careful)
                return f"Error: Expression did not evaluate to a number. Result: {result}"
        except ZeroDivisionError:
            return "Error: Cannot divide by zero."
        except SyntaxError:
            return f"Error: Invalid syntax in expression: '{expression}'."
        except NameError as ne:
             return f"Error: Unknown function or variable in expression: '{expression}'. Details: {ne}"
        except TypeError as te:
            return f"Error: Type error in expression '{expression}'. Check function arguments. Details: {te}"
        except Exception as e:
            # Catch any other unexpected errors
            return f"Error calculating expression '{expression}': {str(e)} (Type: {type(e).__name__})" 