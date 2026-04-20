import re

with open('main.py', 'r') as f:
    code = f.read()

def replacer(match):
    text = match.group(0)
    # Basic conversion from common markdown to HTML just for the strings that have parse_mode="Markdown"
    text = text.replace('parse_mode="Markdown"', 'parse_mode="HTML"')
    # Find all bold **...** and replace with <b>...</b>
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    # Find all italic *...* and replace with <i>...</i>
    text = re.sub(r'(?<!<)\*(.*?)\*(?!>)', r'<i>\1</i>', text)
    # Turn markdown links [text](url) into <a href="url">text</a>
    text = re.sub(r'\[(.*?)\]\((.*?)\)', r'<a href="\2">\1</a>', text)
    return text

# We will apply this replacer only on lines that contain parse_mode="Markdown" 
lines = code.split('\n')
for i in range(len(lines)):
    if 'parse_mode="Markdown"' in lines[i]:
        lines[i] = replacer(re.match(r'.*', lines[i]))

with open('main.py', 'w') as f:
    f.write('\n'.join(lines))
