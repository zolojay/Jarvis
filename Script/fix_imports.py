with open('app_cleaned.py', 'r') as file:
    content = file.read()

content = content.replace('import plotly.express as px\n', '')
content = content.replace('import plotly.graph_objects as go\n', '')

with open('app_cleaned.py', 'w') as file:
    file.write(content)

print("Plotly imports removed from app_cleaned.py") 