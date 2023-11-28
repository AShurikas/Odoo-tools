import ast

def odoo_to_python(domain):
    def parse_condition(condition):
        if isinstance(condition, list):
            if len(condition) == 1:
                return parse_condition(condition[0])
            elif condition[0] == '|':
                return f"{parse_condition(condition[1])} or {parse_condition(condition[2])}"
            else:
                field, operator, value = condition
                return f"{repr(field)} {operator} {repr(value)}"
        return condition

    # Parse the domain expression into a Python expression
    parsed_condition = parse_condition(domain)
    python_expression = f"{{'invisible': {parsed_condition}}}"

    return python_expression

odoo_domain = "{'invisible': ['|', ('amount', '<=', 8), ('amount', '>', 12)]}"

# Convert the Odoo domain expression to Python expression
python_expression = odoo_to_python(ast.literal_eval(odoo_domain))

print(python_expression)