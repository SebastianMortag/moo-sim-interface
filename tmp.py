import itertools


def evaluate_combinations(numbers, operators):
    valid_expressions = []
    eval_count = 0
    for num_comb in itertools.permutations(numbers):
        for op_comb in itertools.product(operators, repeat=3):
            # Generate expressions without brackets
            expression = f"{num_comb[0]}{op_comb[0]}{num_comb[1]}{op_comb[1]}{num_comb[2]}{op_comb[2]}{num_comb[3]}"
            try:
                result = eval(expression)
                valid_expressions.append((expression, result))
            except:
                continue

            # Generate expressions with brackets
            bracket_expressions = [
                f"({num_comb[0]}{op_comb[0]}{num_comb[1]}){op_comb[1]}{num_comb[2]}{op_comb[2]}{num_comb[3]}",
                f"{num_comb[0]}{op_comb[0]}({num_comb[1]}{op_comb[1]}{num_comb[2]}){op_comb[2]}{num_comb[3]}",
                f"{num_comb[0]}{op_comb[0]}{num_comb[1]}{op_comb[1]}({num_comb[2]}{op_comb[2]}{num_comb[3]})",
                f"({num_comb[0]}{op_comb[0]}{num_comb[1]}){op_comb[1]}({num_comb[2]}{op_comb[2]}{num_comb[3]})",
                f"({num_comb[0]}{op_comb[0]}{num_comb[1]}{op_comb[1]}{num_comb[2]}){op_comb[2]}{num_comb[3]}",
                f"{num_comb[0]}{op_comb[0]}({num_comb[1]}{op_comb[1]}{num_comb[2]}{op_comb[2]}{num_comb[3]})"
            ]
            for expr in bracket_expressions:
                try:
                    eval_count += 1
                    result = eval(expr)
                    valid_expressions.append((expr, result))
                except:
                    continue
    print(f"Evaluated {eval_count} expressions.")
    return valid_expressions


if __name__ == '__main__':
    numbers = ['7', '7', '9', '6']
    operators = ['+', '-', '*', '/']
    brackets = ['(', ')']

    valid_expressions = evaluate_combinations(numbers, operators)
    for expr, result in valid_expressions:
        if result == 10:
            print(f"{expr} = {result}")
