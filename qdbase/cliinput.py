def cli_input(prompt, field_def=None, regex=None, value_hint=None, lower=False):
    if field_def == 'yn':
        regex = re.compile(r"[yn]", flags=re.IGNORECASE)
        value_hint = 'y/n'
    if regex is None:
        raise ValueError('No regex defined.')
    if value_hint is None:
        value_prompt = ''
    else:
        value_prompt = " [{}]".format(value_hint)
    while True:
        resp = input("{}{}: ".format(prompt, value_prompt))
        if regex.match(resp):
            break
    if lower:
        resp = resp.lower()
    return resp

def cli_input_symbol(prompt):
    regex = re.compile(r"[a-z]\w", flags=re.ASCII|re.IGNORECASE)
    return cli_input(prompt, regex=regex)

def cli_input_yn(prompt):
    resp = cli_input(prompt, field_def='yn', lower=True)
    if resp == 'y':
        return True
    else:
        return False
