def get_named_parameter(event, name):
    if 'parameters' in event:
        return next(item for item in event['parameters'] if item['name'] == name)['value']
    else:
        return None


def populate_function_response(event, response_body):
    return {'response': {'actionGroup': event['actionGroup'], 'function': event['function'],
                         'functionResponse': {'responseBody': {'TEXT': {'body': str(response_body)}}}}}


def lambda_handler(event, context):
    print(event)
    function = event['function']
    if function == 'transform_string':
        input_string = get_named_parameter(event, 'input_string')
        if not input_string:
            result = f"Error, parameter 'input_string' not supplied"
        else:
            result = input_string.upper()
    else:
        result = f"Error, function '{function}' not recognized"

    response = populate_function_response(event, result)
    print(response)
    return response
